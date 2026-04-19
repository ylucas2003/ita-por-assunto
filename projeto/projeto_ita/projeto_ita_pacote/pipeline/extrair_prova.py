"""
extrair_prova.py — Primeira etapa do pipeline.

Objetivo: dado um PDF de prova do ITA, produzir:
  1. Uma imagem PNG de alta resolução de cada página (para referência visual
     e para recorte posterior de figuras).
  2. Um JSON preliminar por questão contendo:
     - número, enunciado em markdown, alternativas A-E
     - página de origem (e bbox, quando possível)
     - status das flags (texto_extraido, figuras_recortadas, classificado)
  3. Um relatório diagnóstico da prova (quais páginas são nativas, quais
     escaneadas, quais questões provavelmente têm figura).

Uso:
    python extrair_prova.py <pdf_path> --ano 2019 --fase 1 --materia Física

O script é tolerante: se falhar algo em uma questão, marca no status e
continua. Isso evita que uma questão problemática trave a prova inteira.
"""

import argparse
import json
import re
import unicodedata
from pathlib import Path
import fitz  # PyMuPDF

# OCR é opcional — só é usado em páginas escaneadas.
# Se não estiver disponível, o script ainda funciona; apenas marca como aviso.
try:
    import pytesseract
    from PIL import Image
    OCR_DISPONIVEL = True
except ImportError:
    OCR_DISPONIVEL = False


# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

PROJETO_ROOT = Path(__file__).resolve().parent.parent
DIR_PAGINAS = PROJETO_ROOT / "paginas_renderizadas"
DIR_QUESTOES = PROJETO_ROOT / "questoes_json"
DIR_IMAGENS = PROJETO_ROOT / "imagens"

DPI_RENDERIZACAO = 200  # 200 dpi é bom compromisso qualidade/tamanho

# Limite abaixo do qual consideramos a página "escaneada" (texto insuficiente)
LIMITE_TEXTO_ESCANEADA = 100

# Intervalos de questões por matéria — ITA 1ª fase
FAIXAS_MATERIA = {
    "Física":     (1, 12),
    "Português":  (13, 24),
    "Inglês":     (25, 36),
    "Matemática": (37, 48),
    "Química":    (49, 60),
}

# Intervalos do IME: 40 questões, Mat(1-15) Fís(16-30) Quím(31-40)
FAIXAS_MATERIA_IME = {
    "Matemática": (1, 15),
    "Física":     (16, 30),
    "Química":    (31, 40),
}

# Year-specific overrides for ITA: some years changed the question ordering in the PDF.
# 2020-2021: Inglês occupied Q25-40 (16q), Mat = Q41-52, Qui = Q53-60 (8q only).
# 2025: order changed to Mat(1-12) → Fis(13-24) → Por(25-36) → Ing(37-48) → Qui(49-60).
# 2020/2021: Inglês reduced to 10 questions (Q31-40), so each other subject got 15.
#   Física=Q1-15, Português=Q16-30, Inglês=Q31-40, Matemática=Q41-55, Química=Q56-70 (70 total).
# 2025: Dropped Português; order changed to Mat(1-12), Fis(13-24), Por(25-36), Ing(37-48).
#   Only 4 subjects × 12 = 48 total. Química=Q25-36 confirmed by gabarito.
FAIXAS_MATERIA_ITA_ANOS: dict[int, dict[str, tuple]] = {
    2020: {"Física": (1, 15), "Matemática": (41, 55), "Química": (56, 70)},
    2021: {"Física": (1, 15), "Matemática": (41, 55), "Química": (56, 70)},
    2025: {"Física": (13, 24), "Matemática": (1, 12), "Química": (25, 36)},
}

FAIXAS_POR_VESTIBULAR = {
    "ITA": FAIXAS_MATERIA,
    "IME": FAIXAS_MATERIA_IME,
}


# ============================================================================
# UTILITÁRIOS DE TEXTO
# ============================================================================

def normalizar_texto(texto: str) -> str:
    """
    Normaliza texto do PDF para forma Unicode canônica.

    O PDF do ITA é composto em LaTeX (Computer Modern) e por isso contém:
      - Acentos como caracteres combinantes separados ('F´ISICA' em vez de 'FÍSICA')
      - Ligaduras tipográficas ('ﬁ' em vez de 'fi')
      - Símbolos matemáticos remapeados: '!' pode ser ω, '✓' pode ser θ etc.
        (esses vêm porque o PDF embute uma fonte matemática própria e a extração
        lê os glifos por posição, não por Unicode. Corrigimos os mais comuns.)

    Esta função trata todos os casos sistemáticos. Casos idiossincráticos
    sobrarão e devem ser revisados na fase manual.
    """
    # Passo 1: normalização Unicode padrão (resolve a maioria dos acentos)
    texto = unicodedata.normalize("NFC", texto)

    # Passo 2: substituições de acentos combinantes que o NFC não resolve
    acentos = [
        ("´a", "á"), ("´e", "é"), ("´ı", "í"), ("´i", "í"),
        ("´o", "ó"), ("´u", "ú"),
        ("´A", "Á"), ("´E", "É"), ("´I", "Í"), ("´O", "Ó"), ("´U", "Ú"),
        ("˜a", "ã"), ("˜o", "õ"), ("˜A", "Ã"), ("˜O", "Õ"),
        ("ˆa", "â"), ("ˆe", "ê"), ("ˆo", "ô"),
        ("ˆA", "Â"), ("ˆE", "Ê"), ("ˆO", "Ô"),
        ("¸c", "ç"), ("¸C", "Ç"),
        ("`a", "à"), ("`A", "À"),
    ]
    for antes, depois in acentos:
        texto = texto.replace(antes, depois)

    # Passo 3: ligaduras tipográficas (fi, fl, ffi, ffl)
    ligaduras = [
        ("ﬁ", "fi"), ("ﬂ", "fl"), ("ﬀ", "ff"),
        ("ﬃ", "ffi"), ("ﬄ", "ffl"),
    ]
    for antes, depois in ligaduras:
        texto = texto.replace(antes, depois)

    # Passo 4: símbolos "matemáticos falsos" vindos de fontes embutidas.
    # ATENÇÃO: essas substituições são contextuais e podem gerar falsos positivos
    # em texto normal. Por isso só aplicamos dentro de contextos matemáticos óbvios
    # (entre parênteses, ou após símbolos matemáticos conhecidos).
    # Na prática, é mais seguro preservar os caracteres originais e deixar a
    # revisão humana trocar pelos LaTeX corretos.
    # Por enquanto, apenas marcamos com uma nota — NÃO substituímos automaticamente.

    # Passo 5: espaços em branco
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)

    return texto.strip()


# ============================================================================
# ANÁLISE DA PÁGINA
# ============================================================================

def analisar_pagina(page: fitz.Page) -> dict:
    """
    Diagnostica o tipo da página para escolher a estratégia de extração.

    Retorna um dict com:
      - tipo: 'nativa' (texto selecionável) ou 'escaneada' (imagem pura)
      - texto: o texto extraível (vazio se escaneada)
      - num_desenhos_vetoriais: indicador de figuras feitas em vetor
      - num_imagens_embutidas: imagens rasterizadas embutidas
    """
    texto = page.get_text()
    desenhos = page.get_drawings()
    imagens = page.get_images(full=True)

    if len(texto.strip()) < LIMITE_TEXTO_ESCANEADA:
        tipo = "escaneada"
    else:
        tipo = "nativa"

    return {
        "tipo": tipo,
        "texto_bruto": texto,
        "num_desenhos_vetoriais": len(desenhos),
        "num_imagens_embutidas": len(imagens),
    }


# ============================================================================
# SEGMENTAÇÃO DE QUESTÕES
# ============================================================================

# Regex captura "Questão N." ou "Questao N." ou "Quest˜ao N."
PADRAO_QUESTAO = re.compile(
    r"Quest(?:ão|ao|˜ao)\s*(\d{1,2})\s*\.\s*",
    flags=re.IGNORECASE,
)

# IME: "1ª QUESTÃO", "16ª QUESTÃO" …
# Allow optional space before ÃO because some PDFs encode "QUEST˜AO" with a space
# before the combining tilde, which after normalization becomes "QUEST ÃO".
PADRAO_QUESTAO_IME = re.compile(
    r"(\d{1,2})ª?\s*QUEST\s*[ÃA]O",
    flags=re.IGNORECASE,
)


def segmentar_questoes(texto_completo: str, faixa_numeros: tuple, padrao=None) -> list[dict]:
    """
    Divide o texto completo da prova em questões individuais.

    faixa_numeros: tupla (primeiro, ultimo) — ex: (1, 12) para Física.
    padrao: regex compilado a usar (default: PADRAO_QUESTAO para ITA).
    """
    p = padrao if padrao is not None else PADRAO_QUESTAO
    matches = list(p.finditer(texto_completo))
    primeiro, ultimo = faixa_numeros

    # Filtra apenas matches cujo número está na faixa
    matches_validos = [m for m in matches if primeiro <= int(m.group(1)) <= ultimo]

    questoes = []
    for i, m in enumerate(matches_validos):
        num = int(m.group(1))
        inicio = m.end()
        # O texto da questão vai até o início da próxima questão válida,
        # ou até o fim do texto se for a última.
        if i + 1 < len(matches_validos):
            fim = matches_validos[i + 1].start()
        else:
            fim = len(texto_completo)

        texto_questao = texto_completo[inicio:fim].strip()
        questoes.append({"numero": num, "texto_bruto": texto_questao})

    return questoes


# ============================================================================
# EXTRAÇÃO DE ALTERNATIVAS
# ============================================================================

# ITA: "A ( )", "A( )" etc.
PADRAO_ALTERNATIVA = re.compile(
    r"\b([A-E])\s*\(\s*\)\s*",
)

# IME: "(A) texto", "(B) texto" etc.
PADRAO_ALTERNATIVA_IME = re.compile(
    r"\(([A-E])\)\s*",
)


def extrair_enunciado_e_alternativas(texto_questao: str, padrao_alt=None) -> dict:
    """
    Separa o enunciado das 5 alternativas (A-E).

    padrao_alt: regex compilado (default: PADRAO_ALTERNATIVA para ITA).
    """
    p = padrao_alt if padrao_alt is not None else PADRAO_ALTERNATIVA
    matches = list(p.finditer(texto_questao))

    if len(matches) < 5:
        # Fallback: não conseguimos identificar as 5 alternativas.
        # Pode acontecer em questões escaneadas antes do OCR, ou em casos raros.
        return {
            "enunciado_md": texto_questao.strip(),
            "alternativas": {},
            "alternativas_extraidas": False,
        }

    # Primeiro match delimita o fim do enunciado
    enunciado = texto_questao[:matches[0].start()].strip()

    alternativas = {}
    for i, m in enumerate(matches[:5]):  # só as 5 primeiras (A-E)
        letra = m.group(1).upper()
        inicio = m.end()
        fim = matches[i + 1].start() if i + 1 < len(matches[:5]) else len(texto_questao)
        texto_alt = texto_questao[inicio:fim].strip()
        # Remove quebras de linha excessivas dentro da alternativa
        texto_alt = re.sub(r"\s+", " ", texto_alt)
        alternativas[letra] = texto_alt

    return {
        "enunciado_md": enunciado,
        "alternativas": alternativas,
        "alternativas_extraidas": len(alternativas) == 5,
    }


# ============================================================================
# DETECÇÃO DE PROVÁVEL FIGURA
# ============================================================================

PALAVRAS_INDICAM_FIGURA = [
    "figura", "mostra", "conforme", "ilustrad", "esquema",
    "gráfico", "diagrama", "abaixo", "ao lado",
]


def provavelmente_tem_figura(enunciado: str, pagina_info: dict) -> bool:
    """
    Heurística para marcar se a questão possivelmente tem figura.

    Critérios (qualquer um dispara):
      - Enunciado menciona palavras indicativas.
      - A página tem muitos desenhos vetoriais (>15 paths).
      - A página é escaneada (nesse caso, presumimos que pode ter figura).

    Esta marcação é só uma sugestão — na fase de revisão manual você
    confirma ou descarta.
    """
    texto_lower = enunciado.lower()
    if any(palavra in texto_lower for palavra in PALAVRAS_INDICAM_FIGURA):
        return True
    if pagina_info.get("num_desenhos_vetoriais", 0) > 15:
        return True
    if pagina_info.get("tipo") == "escaneada":
        return True
    return False


# ============================================================================
# PIPELINE PRINCIPAL
# ============================================================================

def processar_pdf(
    pdf_path: Path,
    ano: int,
    fase: int,
    materia: str,
    vestibular: str = "ITA",
) -> dict:
    """
    Processa um PDF de prova e salva JSONs + imagens de páginas.

    Retorna um relatório diagnóstico.
    """
    if vestibular.upper() == "ITA" and ano in FAIXAS_MATERIA_ITA_ANOS:
        faixas = FAIXAS_MATERIA_ITA_ANOS[ano]
    else:
        faixas = FAIXAS_POR_VESTIBULAR.get(vestibular.upper(), FAIXAS_MATERIA)
    assert materia in faixas, \
        f"Matéria {materia!r} não reconhecida para {vestibular} {ano} (faixas disponíveis: {list(faixas)})"
    faixa = faixas[materia]

    is_ime = vestibular.upper() == "IME"
    padrao_q = PADRAO_QUESTAO_IME if is_ime else PADRAO_QUESTAO
    padrao_alt = PADRAO_ALTERNATIVA_IME if is_ime else PADRAO_ALTERNATIVA

    SUFIXO_MATERIA = {
        "Física": "", "Química": "_qui", "Matemática": "_mat",
        "Português": "_por", "Inglês": "_ing",
    }
    prova_id = f"{vestibular.lower()}_{ano}"
    if fase:
        prova_id += f"_fase{fase}"
    prova_id += SUFIXO_MATERIA.get(materia, f"_{materia.lower()[:3]}")

    # Pastas específicas desta prova
    dir_paginas_prova = DIR_PAGINAS / prova_id
    dir_questoes_prova = DIR_QUESTOES / prova_id
    dir_paginas_prova.mkdir(parents=True, exist_ok=True)
    dir_questoes_prova.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    relatorio = {
        "prova_id": prova_id,
        "pdf": str(pdf_path),
        "materia": materia,
        "paginas": [],
        "questoes_extraidas": [],
        "avisos": [],
    }

    # ------------------------------------------------------------------
    # Etapa 1: renderizar cada página como PNG e coletar texto.
    # O texto é coletado página a página e concatenado depois.
    # ------------------------------------------------------------------
    texto_completo = ""
    # Mapa auxiliar: para cada trecho de texto, sabemos a qual página pertence.
    # Usamos isso depois para identificar em que página cada questão está.
    marcos_pagina = []  # lista de (offset_acumulado, num_pagina)

    for num_pag, page in enumerate(doc, start=1):
        info = analisar_pagina(page)
        relatorio["paginas"].append({
            "numero": num_pag,
            "tipo": info["tipo"],
            "desenhos_vetoriais": info["num_desenhos_vetoriais"],
            "imagens_embutidas": info["num_imagens_embutidas"],
        })

        # Renderiza a página como PNG de alta resolução
        pix = page.get_pixmap(dpi=DPI_RENDERIZACAO)
        png_path = dir_paginas_prova / f"pagina_{num_pag:02d}.png"
        pix.save(str(png_path))

        # Estratégia: se a página é nativa, usa texto do PDF direto.
        # Se é escaneada, roda OCR na imagem renderizada (se disponível).
        texto_pagina = info["texto_bruto"]
        if info["tipo"] == "escaneada":
            if OCR_DISPONIVEL:
                try:
                    # OCR em português. Configuração "psm 6" = bloco uniforme,
                    # que funciona bem para páginas de prova.
                    img = Image.open(png_path)
                    texto_ocr = pytesseract.image_to_string(
                        img, lang="por", config="--psm 6"
                    )
                    texto_pagina = texto_ocr
                    relatorio["avisos"].append(
                        f"Página {num_pag} (escaneada): texto obtido via OCR. "
                        f"Revise com atenção — OCR pode cometer erros."
                    )
                except Exception as e:
                    relatorio["avisos"].append(
                        f"Página {num_pag} é escaneada e o OCR falhou: {e}"
                    )
            else:
                relatorio["avisos"].append(
                    f"Página {num_pag} é escaneada e OCR não está disponível. "
                    f"Instale pytesseract + tesseract-ocr-por."
                )

        marcos_pagina.append((len(texto_completo), num_pag))
        texto_completo += "\n" + texto_pagina

    texto_completo = normalizar_texto(texto_completo)

    # ------------------------------------------------------------------
    # Etapa 2: segmentar questões da matéria pedida.
    # ------------------------------------------------------------------
    questoes_brutas = segmentar_questoes(texto_completo, faixa, padrao=padrao_q)

    if len(questoes_brutas) < (faixa[1] - faixa[0] + 1):
        relatorio["avisos"].append(
            f"Esperava {faixa[1] - faixa[0] + 1} questões de {materia}, "
            f"encontrei {len(questoes_brutas)}. Possível causa: questões em "
            f"páginas escaneadas."
        )

    # ------------------------------------------------------------------
    # Etapa 3: para cada questão, extrair alt's, descobrir página, salvar JSON.
    # ------------------------------------------------------------------
    def descobrir_pagina(offset_questao: int) -> int:
        """Dado o offset textual de uma questão, retorna o nº da página."""
        pagina_encontrada = 1
        for offset, pag in marcos_pagina:
            if offset <= offset_questao:
                pagina_encontrada = pag
            else:
                break
        return pagina_encontrada

    # Precisamos re-localizar cada questão no texto normalizado para pegar offset
    for q_bruta in questoes_brutas:
        num = q_bruta["numero"]

        # Procura no texto_completo o offset desta questão
        if is_ime:
            padrao_num = re.compile(rf"{num}ª?\s*QUEST\s*[ÃA]O", re.IGNORECASE)
        else:
            padrao_num = re.compile(rf"Quest(?:ão|ao|˜ao)\s*{num}\s*\.", re.IGNORECASE)
        m = padrao_num.search(texto_completo)
        offset = m.start() if m else 0
        pagina = descobrir_pagina(offset)
        info_pagina = relatorio["paginas"][pagina - 1]

        # Separa enunciado e alternativas
        partes = extrair_enunciado_e_alternativas(q_bruta["texto_bruto"], padrao_alt=padrao_alt)

        tem_figura = provavelmente_tem_figura(partes["enunciado_md"], info_pagina)

        questao_json = {
            "id": f"{prova_id}_q{num:02d}",
            "prova": {
                "vestibular": vestibular,
                "ano": ano,
                "fase": fase,
                "materia": materia,
            },
            "numero": num,
            "enunciado_md": partes["enunciado_md"],
            "alternativas": partes["alternativas"],
            "gabarito": None,  # preenchido depois pelo script de gabarito
            "imagens": [],
            "classificacao": {
                "topicos_ids": [],
                "topicos_nomes": [],
                "blocos": [],
                "classificado_por": None,
                "confianca": None,
                "observacao": "",
            },
            "fonte": {
                "pdf": pdf_path.name,
                "pagina": pagina,
                "bbox_questao": None,
            },
            "status": {
                "texto_extraido": bool(partes["enunciado_md"]),
                "alternativas_extraidas": partes["alternativas_extraidas"],
                "figuras_recortadas": not tem_figura,  # true se não precisa
                "classificado": False,
                "revisado": False,
                "possivelmente_tem_figura": tem_figura,
            },
        }

        # Salva o JSON
        json_path = dir_questoes_prova / f"q{num:02d}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(questao_json, f, ensure_ascii=False, indent=2)

        relatorio["questoes_extraidas"].append({
            "numero": num,
            "pagina": pagina,
            "alternativas_ok": partes["alternativas_extraidas"],
            "possivelmente_tem_figura": tem_figura,
        })

    # Salva o relatório
    rel_path = dir_questoes_prova / "_relatorio.json"
    with open(rel_path, "w", encoding="utf-8") as f:
        json.dump(relatorio, f, ensure_ascii=False, indent=2)

    return relatorio


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Extrai questões de um PDF do ITA.")
    parser.add_argument("pdf", type=Path, help="Caminho para o PDF da prova")
    parser.add_argument("--ano", type=int, required=True)
    parser.add_argument("--fase", type=int, default=1)
    _all_materias = list(dict.fromkeys(list(FAIXAS_MATERIA.keys()) + list(FAIXAS_MATERIA_IME.keys())))
    parser.add_argument("--materia", default="Física", choices=_all_materias)
    parser.add_argument("--vestibular", default="ITA")

    args = parser.parse_args()

    relatorio = processar_pdf(
        pdf_path=args.pdf,
        ano=args.ano,
        fase=args.fase,
        materia=args.materia,
        vestibular=args.vestibular,
    )

    print(f"\n=== Extração concluída: {relatorio['prova_id']} ===")
    print(f"Matéria: {relatorio['materia']}")
    print(f"Questões extraídas: {len(relatorio['questoes_extraidas'])}")

    if relatorio["avisos"]:
        print(f"\n⚠ Avisos ({len(relatorio['avisos'])}):")
        for aviso in relatorio["avisos"]:
            print(f"  - {aviso}")

    com_figura = [q for q in relatorio["questoes_extraidas"] if q["possivelmente_tem_figura"]]
    if com_figura:
        print(f"\n📷 Questões que provavelmente têm figura (revisar):")
        for q in com_figura:
            print(f"  Q{q['numero']:02d} (pg {q['pagina']})")


if __name__ == "__main__":
    main()
