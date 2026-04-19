"""
renderizar_html.py — Etapa 5 (final) do pipeline.

Gera um HTML com as questões organizadas por tópico, incluindo:
  - Cabeçalho com título e metadados
  - Índice clicável
  - Questões renderizadas (usando as imagens recortadas)
  - Gabarito
  - Estatísticas de recorrência por tópico

Uso:
    # Gerar simulado com todas as questões de uma ou várias provas
    python renderizar_html.py --provas ita_2019_fase1 --titulo "Simulado ITA 2019"

    # Filtrar por bloco temático (uma ou mais provas)
    python renderizar_html.py --provas ita_2019_fase1 ita_2020_fase1 \
           --bloco "Eletromagnetismo" --titulo "Simulado Eletromagnetismo"

    # Filtrar por tópico específico
    python renderizar_html.py --provas ita_2019_fase1 --topico 7.1

O HTML gerado é autocontido: todas as imagens são codificadas em base64
dentro do próprio arquivo (opção --embed) ou referenciadas por caminho relativo.
Se optar por caminhos relativos, copie a pasta `imagens/` junto ao HTML
quando for compartilhar.
"""

import argparse
import base64
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from jinja2 import Template


PROJETO_ROOT = Path(__file__).resolve().parent.parent
DIR_QUESTOES_JSON = PROJETO_ROOT / "questoes_json"
DIR_OUTPUT = PROJETO_ROOT / "output"
TAXONOMIA_POR_MATERIA = {
    "Física":     "taxonomia.json",
    "Química":    "taxonomia_quimica.json",
    "Matemática": "taxonomia_matematica.json",
}


# ============================================================================
# TEMPLATE HTML
# ============================================================================

# O template é minimalista e semântico:
#   <article class="questao"> encapsula cada questão (fácil de manipular / estilizar)
#   <img class="questao-imagem"> é o recorte PNG
#   Os metadados (tópicos, gabarito) ficam em data-attributes para
#   transformação fácil em LaTeX/DOCX depois.

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>{{ titulo }}</title>
<style>
  body {
    font-family: Georgia, 'Times New Roman', serif;
    max-width: 900px;
    margin: 2em auto;
    padding: 0 1.5em;
    color: #222;
    line-height: 1.5;
  }
  header {
    border-bottom: 2px solid #333;
    margin-bottom: 2em;
    padding-bottom: 1em;
  }
  h1 { margin: 0 0 0.3em 0; font-size: 1.8em; }
  .subtitulo { color: #666; font-size: 0.95em; }
  h2 {
    margin-top: 2em;
    padding: 0.4em 0.6em;
    background: #f0f0f0;
    border-left: 5px solid #555;
    font-size: 1.3em;
  }
  h3 {
    margin-top: 1.5em;
    color: #555;
    font-size: 1.1em;
  }
  nav.indice {
    background: #fafafa;
    border: 1px solid #ddd;
    padding: 1em 1.5em;
    margin: 1em 0 2em 0;
    border-radius: 4px;
  }
  nav.indice ul { padding-left: 1.2em; }
  nav.indice li { margin: 0.2em 0; }
  article.questao {
    margin: 1.5em 0 2em 0;
    padding: 1em;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    page-break-inside: avoid;
  }
  article.questao .meta {
    font-size: 0.85em;
    color: #888;
    margin-bottom: 0.5em;
  }
  article.questao .meta .tag {
    display: inline-block;
    background: #eef;
    color: #446;
    padding: 1px 7px;
    margin-right: 4px;
    border-radius: 3px;
    font-size: 0.88em;
  }
  img.questao-imagem {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 0.5em 0;
  }
  .obs {
    font-style: italic;
    color: #777;
    font-size: 0.88em;
    margin-top: 0.4em;
  }
  table.gabarito, table.stats {
    border-collapse: collapse;
    margin: 1em 0;
  }
  table.gabarito td, table.gabarito th,
  table.stats td, table.stats th {
    border: 1px solid #bbb;
    padding: 6px 12px;
    text-align: center;
  }
  table.gabarito th, table.stats th {
    background: #eee;
  }
  .barra {
    display: inline-block;
    height: 14px;
    background: #6688cc;
    vertical-align: middle;
  }
  @media print {
    article.questao { border-color: #ccc; }
    h2 { page-break-before: always; }
    h2:first-of-type { page-break-before: avoid; }
  }
</style>
</head>
<body>

<header>
  <h1>{{ titulo }}</h1>
  <div class="subtitulo">
    Gerado em {{ data_geracao }} · {{ total_questoes }} questões ·
    {{ provas|join(', ') }}
  </div>
</header>

<nav class="indice">
  <strong>Índice</strong>
  <ul>
    {% for bloco in blocos_presentes %}
      <li><a href="#bloco-{{ bloco.slug }}">{{ bloco.nome }}</a>
          ({{ bloco.num_questoes }} questões)</li>
    {% endfor %}
    <li><a href="#gabarito">Gabarito</a></li>
    <li><a href="#estatisticas">Estatísticas de recorrência</a></li>
  </ul>
</nav>

{% for bloco in blocos_presentes %}
  <h2 id="bloco-{{ bloco.slug }}">{{ bloco.nome }}</h2>

  {% for subbloco in bloco.subblocos %}
    {% if subbloco.nome != bloco.nome %}
      <h3>{{ subbloco.id }} {{ subbloco.nome }}</h3>
    {% endif %}

    {% for q in subbloco.questoes %}
      <article class="questao"
               data-id="{{ q.id }}"
               data-topicos="{{ q.classificacao.topicos_ids|join(',') }}"
               data-gabarito="{{ q.gabarito or '?' }}">
        <div class="meta">
          <strong>{{ q.prova.vestibular }} {{ q.prova.ano }}</strong>
          · Questão {{ q.numero }}
          {% for tid in q.classificacao.topicos_ids %}
            <span class="tag">{{ tid }}</span>
          {% endfor %}
        </div>
        {% if q.imagem_questao %}
          <img class="questao-imagem" src="{{ q.img_src }}"
               alt="Questão {{ q.numero }}">
        {% else %}
          <div>{{ q.enunciado_md }}</div>
          <ol type="A">
            {% for letra, texto in q.alternativas.items() %}
              <li>{{ texto }}</li>
            {% endfor %}
          </ol>
        {% endif %}
        {% if q.classificacao.observacao %}
          <div class="obs">{{ q.classificacao.observacao }}</div>
        {% endif %}
      </article>
    {% endfor %}
  {% endfor %}
{% endfor %}

<h2 id="gabarito">Gabarito</h2>
<table class="gabarito">
  <thead>
    <tr><th>Questão</th><th>Prova</th><th>Resposta</th><th>Tópicos</th></tr>
  </thead>
  <tbody>
    {% for q in todas_questoes_ordenadas %}
      <tr>
        <td>{{ q.numero }}</td>
        <td>{{ q.prova.vestibular }} {{ q.prova.ano }}</td>
        <td><strong>{{ q.gabarito or '?' }}</strong></td>
        <td>{{ q.classificacao.topicos_ids|join(', ') }}</td>
      </tr>
    {% endfor %}
  </tbody>
</table>

<h2 id="estatisticas">Estatísticas de Recorrência</h2>

<h3>Por bloco temático</h3>
<table class="stats">
  <thead><tr><th>Bloco</th><th>Questões</th><th>%</th><th>Frequência</th></tr></thead>
  <tbody>
    {% for item in stats_blocos %}
      <tr>
        <td style="text-align:left">{{ item.nome }}</td>
        <td>{{ item.count }}</td>
        <td>{{ "%.1f"|format(item.pct) }}%</td>
        <td style="text-align:left">
          <span class="barra" style="width:{{ item.pct * 3 }}px"></span>
        </td>
      </tr>
    {% endfor %}
  </tbody>
</table>

<h3>Por subárea (tópico específico)</h3>
<table class="stats">
  <thead><tr><th>ID</th><th>Subárea</th><th>Questões</th><th>%</th></tr></thead>
  <tbody>
    {% for item in stats_subblocos %}
      <tr>
        <td>{{ item.id }}</td>
        <td style="text-align:left">{{ item.nome }}</td>
        <td>{{ item.count }}</td>
        <td>{{ "%.1f"|format(item.pct) }}%</td>
      </tr>
    {% endfor %}
  </tbody>
</table>

<p style="margin-top:3em; font-size:0.85em; color:#888; text-align:center">
  Gerado pelo pipeline ITA. Fonte canônica: JSONs em questoes_json/.
</p>

</body>
</html>
"""


# ============================================================================
# CARREGAMENTO E FILTRO
# ============================================================================

def carregar_taxonomia(materia: str = "Física") -> dict:
    nome = TAXONOMIA_POR_MATERIA.get(materia, "taxonomia.json")
    with open(PROJETO_ROOT / "config" / nome, encoding="utf-8") as f:
        return json.load(f)


def slugify(texto: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", texto.lower()).strip("-")


def carregar_questoes(prova_ids: list[str]) -> list[dict]:
    questoes = []
    for pid in prova_ids:
        dir_prova = DIR_QUESTOES_JSON / pid
        if not dir_prova.exists():
            print(f"⚠ Pasta não encontrada: {dir_prova}")
            continue
        for jp in sorted(dir_prova.glob("q*.json")):
            with open(jp, encoding="utf-8") as f:
                questoes.append(json.load(f))
    return questoes


def filtrar(questoes, bloco=None, topico=None):
    if bloco:
        questoes = [
            q for q in questoes
            if bloco in q["classificacao"].get("blocos", [])
        ]
    if topico:
        questoes = [
            q for q in questoes
            if topico in q["classificacao"].get("topicos_ids", [])
        ]
    return questoes


# ============================================================================
# AGRUPAMENTO PARA RENDERIZAÇÃO
# ============================================================================

def agrupar_por_bloco(questoes: list[dict], taxonomia: dict):
    """
    Organiza as questões na mesma ordem da taxonomia do edital, agrupadas
    por bloco e subbloco. Só inclui blocos/subblocos que têm questões.
    """
    # Mapa {id_subbloco: [questões]}
    por_sub = defaultdict(list)
    for q in questoes:
        # Usa o PRIMEIRO tópico para colocar a questão em um grupo principal.
        # (As tags ainda mostram todos os tópicos dela.)
        ids = q["classificacao"].get("topicos_ids", [])
        primeiro_id = ids[0] if ids else "0.0"
        por_sub[primeiro_id].append(q)

    blocos_presentes = []
    for bloco in taxonomia["blocos"]:
        subblocos_com_q = []
        total_no_bloco = 0
        for sub in bloco["subareas"]:
            qs = por_sub.get(sub["id"], [])
            if qs:
                qs_ordenadas = sorted(
                    qs, key=lambda q: (q["prova"]["ano"], q["numero"])
                )
                subblocos_com_q.append({
                    "id": sub["id"],
                    "nome": sub["nome"],
                    "questoes": qs_ordenadas,
                })
                total_no_bloco += len(qs_ordenadas)

        if subblocos_com_q:
            blocos_presentes.append({
                "id": bloco["id"],
                "nome": bloco["nome"],
                "slug": slugify(bloco["nome"]),
                "subblocos": subblocos_com_q,
                "num_questoes": total_no_bloco,
            })
    return blocos_presentes


# ============================================================================
# ESTATÍSTICAS
# ============================================================================

def calcular_estatisticas(questoes: list[dict], taxonomia: dict):
    """
    Para cada questão que tem N tópicos, contamos 1/N para cada tópico
    (assim a soma das contagens bate com o total de questões — evita
    inflar estatísticas em questões mistas).
    """
    bloco_por_subid = {}
    nome_por_subid = {}
    for bloco in taxonomia["blocos"]:
        for sub in bloco["subareas"]:
            bloco_por_subid[sub["id"]] = bloco["nome"]
            nome_por_subid[sub["id"]] = sub["nome"]

    contador_sub = defaultdict(float)
    contador_bloco = defaultdict(float)

    for q in questoes:
        ids = q["classificacao"].get("topicos_ids", [])
        if not ids:
            contador_sub["0.0"] += 1
            contador_bloco["Não classificada"] += 1
            continue
        peso = 1 / len(ids)
        for tid in ids:
            contador_sub[tid] += peso
            contador_bloco[bloco_por_subid.get(tid, "Desconhecido")] += peso

    total = len(questoes) or 1

    stats_blocos = [
        {"nome": nome, "count": round(c, 2), "pct": 100 * c / total}
        for nome, c in contador_bloco.items()
    ]
    stats_blocos.sort(key=lambda x: -x["count"])

    stats_subblocos = [
        {
            "id": tid,
            "nome": nome_por_subid.get(tid, "?"),
            "count": round(c, 2),
            "pct": 100 * c / total,
        }
        for tid, c in contador_sub.items()
    ]
    stats_subblocos.sort(key=lambda x: -x["count"])

    return stats_blocos, stats_subblocos


# ============================================================================
# RENDERIZAÇÃO
# ============================================================================

def resolver_caminho_imagem(q: dict, embed: bool, html_dir: Path) -> str:
    """Retorna src da imagem: URL S3 se disponível, data-URI se embed, ou path local."""
    if q.get("imagem_questao_url"):
        return q["imagem_questao_url"]
    caminho_rel = q.get("imagem_questao")
    if not caminho_rel:
        return ""
    caminho_abs = PROJETO_ROOT / caminho_rel
    if not caminho_abs.exists():
        return ""
    if embed:
        b64 = base64.b64encode(caminho_abs.read_bytes()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    else:
        try:
            return str(caminho_abs.relative_to(html_dir))
        except ValueError:
            return str(caminho_abs)


def renderizar(
    prova_ids: list[str],
    titulo: str,
    bloco: str = None,
    topico: str = None,
    embed: bool = True,
    arquivo_saida: str = None,
):
    questoes = carregar_questoes(prova_ids)
    questoes = filtrar(questoes, bloco=bloco, topico=topico)
    materia = questoes[0]["prova"]["materia"] if questoes else "Física"
    taxonomia = carregar_taxonomia(materia)

    if not questoes:
        print("Nenhuma questão encontrada com os filtros.")
        return

    DIR_OUTPUT.mkdir(exist_ok=True)
    if arquivo_saida:
        html_path = DIR_OUTPUT / arquivo_saida
    else:
        nome = titulo.lower().replace(" ", "_")
        nome = re.sub(r"[^a-z0-9_]", "", nome)
        html_path = DIR_OUTPUT / f"{nome}.html"

    # Resolve imagens
    for q in questoes:
        q["img_src"] = resolver_caminho_imagem(q, embed, html_path.parent)

    blocos_presentes = agrupar_por_bloco(questoes, taxonomia)
    stats_blocos, stats_subblocos = calcular_estatisticas(questoes, taxonomia)

    todas_ordenadas = sorted(
        questoes, key=lambda q: (q["prova"]["ano"], q["numero"])
    )

    template = Template(HTML_TEMPLATE)
    html = template.render(
        titulo=titulo,
        data_geracao=datetime.now().strftime("%d/%m/%Y %H:%M"),
        total_questoes=len(questoes),
        provas=sorted(set(f"{q['prova']['vestibular']} {q['prova']['ano']}" for q in questoes)),
        blocos_presentes=blocos_presentes,
        todas_questoes_ordenadas=todas_ordenadas,
        stats_blocos=stats_blocos,
        stats_subblocos=stats_subblocos,
    )

    html_path.write_text(html, encoding="utf-8")
    print(f"✓ HTML gerado: {html_path}")
    print(f"  {len(questoes)} questões · {len(blocos_presentes)} blocos temáticos")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provas", nargs="+", required=True)
    parser.add_argument("--titulo", default="Simulado ITA")
    parser.add_argument("--bloco", default=None, help="Filtrar por nome do bloco")
    parser.add_argument("--topico", default=None, help="Filtrar por ID de tópico (ex: 8.3)")
    parser.add_argument("--no-embed", action="store_true",
                        help="Referenciar imagens por path em vez de embutir em base64")
    parser.add_argument("--saida", default=None, help="Nome do arquivo HTML de saída")
    args = parser.parse_args()

    renderizar(
        prova_ids=args.provas,
        titulo=args.titulo,
        bloco=args.bloco,
        topico=args.topico,
        embed=not args.no_embed,
        arquivo_saida=args.saida,
    )


if __name__ == "__main__":
    main()
