#!/usr/bin/env python3
"""
gerar_banco_unificado.py — HTML único com Física, Química e Matemática,
com sidebar lateral para navegar por matéria e assunto.

Uso:
    python pipeline/gerar_banco_unificado.py
"""

import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

PROJETO_ROOT = Path(__file__).resolve().parent.parent
DIR_QUESTOES_JSON = PROJETO_ROOT / "questoes_json"
DIR_OUTPUT = PROJETO_ROOT / "output"

MATERIAS_CONFIG = [
    {
        "nome": "Física",
        "sufixo": "",
        "taxonomia": "taxonomia.json",
        "cor": "#4a7fc1",
        "cor_claro": "#eef2fb",
    },
    {
        "nome": "Química",
        "sufixo": "_qui",
        "taxonomia": "taxonomia_quimica.json",
        "cor": "#2a9d6f",
        "cor_claro": "#e6f5ee",
    },
    {
        "nome": "Matemática",
        "sufixo": "_mat",
        "taxonomia": "taxonomia_matematica.json",
        "cor": "#c9622a",
        "cor_claro": "#faeee6",
    },
]


def carregar_taxonomia(nome_arquivo: str) -> dict:
    with open(PROJETO_ROOT / "config" / nome_arquivo, encoding="utf-8") as f:
        return json.load(f)


def descobrir_provas(sufixo: str) -> list[str]:
    result = []
    outros_sufixos = ("_qui", "_mat", "_por", "_ing")
    for d in sorted(DIR_QUESTOES_JSON.iterdir()):
        if not d.is_dir():
            continue
        nome = d.name
        if sufixo == "":
            if re.search(r"fase\d$", nome) and not any(nome.endswith(s) for s in outros_sufixos):
                result.append(nome)
        else:
            if nome.endswith(sufixo):
                result.append(nome)
    return result


def carregar_questoes(prova_ids: list[str]) -> list[dict]:
    questoes = []
    for pid in prova_ids:
        d = DIR_QUESTOES_JSON / pid
        if not d.exists():
            continue
        for jp in sorted(d.glob("q*.json")):
            with open(jp, encoding="utf-8") as f:
                questoes.append(json.load(f))
    return questoes


SUFIXO_GAL = {"": 1, "_mat": 4, "_qui": 5}   # ITA 1st-phase gallery IDs (2022-2024)
SUFIXO_OFF = {"": 0, "_mat": 36, "_qui": 48}  # absolute-number offset per subject

# ITA 2nd-phase gallery IDs for the 2022-2023 layout (servicos.aridesa.com.br/comentario/ita/{ano})
ITA_F2_GAL_2022_2023 = {"_mat": 6, "_qui": 7, "": 8}

# ITA 2nd-phase slide offsets for 2025+ (comentarios.aridesa.com.br/ita?...&stage=2)
# Mat Q1 at slide 1, Qui Q1 at slide 11; Fis Q1 depends on how many Qui slides were comentadas.
ITA_F2_OFF_2025_PLUS = {
    2025: {"_mat": 0, "_qui": 10, "": 20},
    2026: {"_mat": 0, "_qui": 10, "": 19},
}

# IME reference_ids for comentarios.aridesa.com.br (no formula — hard-coded)
IME_REF_IDS = {2023: 3, 2024: 2, 2025: 4}

# IME 1st-phase Aridesa gallery layout (2021-2022):
# gallery-1 = Matemática (1-15), gallery-2 = Física (16-30), gallery-3 = Química (31-40)
IME_GAL = {"_mat": 1, "": 2, "_qui": 3}
IME_OFF = {"_mat": 0, "": 15, "_qui": 30}


def url_resolucao_fase1(sufixo: str, vestibular: str, ano: int, numero: int) -> str:
    """Return the Aridesa resolution URL for a 1st-phase question, or '' if unknown."""
    if vestibular == "IME":
        if ano in IME_REF_IDS:
            # 2023-2025: all 40 questions share gallery-1 (1-indexed by numero)
            return f"https://comentarios.aridesa.com.br/ime?reference_id={IME_REF_IDS[ano]}#gallery-1-{numero}"
        if ano in (2021, 2022):
            gid = IME_GAL.get(sufixo, 1)
            within = numero - IME_OFF.get(sufixo, 0)
            slug = f"{ano}-{ano + 1}"
            return f"https://servicos.aridesa.com.br/comentario/ime/{slug}/#gallery-{gid}-{within}"
        if ano == 2020:
            return "http://login.aridesa.com.br/vestibular/ime2020_2021/index.aspx"
        if ano == 2019:
            return "http://login.aridesa.com.br/vestibular/ime2019_2020/index.aspx"
        if ano == 2018:
            return "http://login.aridesa.com.br/vestibular/ime2018_2019/index.aspx"
        return ""
    if vestibular != "ITA":
        return ""
    if ano >= 2025:
        ref = ano - 2024
        return f"https://comentarios.aridesa.com.br/ita?reference_id={ref}#gallery-1-{numero}"
    if ano >= 2022:
        gid = SUFIXO_GAL.get(sufixo, 1)
        within_q = numero - SUFIXO_OFF.get(sufixo, 0)
        return f"https://servicos.aridesa.com.br/comentario/ita/{ano}/#gallery-{gid}-{within_q}"
    if ano >= 2019:
        return f"http://login.aridesa.com.br/vestibular/ita{ano}/index.aspx"
    return ""


def url_resolucao_fase2(sufixo: str, vestibular: str, ano: int, numero: int) -> str:
    """Return the Aridesa resolution URL for a 2nd-phase question, or '' if unknown."""
    if vestibular != "ITA":
        return ""
    if ano >= 2025:
        ref = ano - 2024
        offsets = ITA_F2_OFF_2025_PLUS.get(ano, ITA_F2_OFF_2025_PLUS[2025])
        slide = numero + offsets.get(sufixo, 0)
        return f"https://comentarios.aridesa.com.br/ita?reference_id={ref}&stage=2#gallery-1-{slide}"
    if ano == 2024:
        # Same galleries as 1ª fase, mas Q1 da 2ª fase começa no slide 13 (offset 12)
        gid = SUFIXO_GAL.get(sufixo, 1)
        slide = numero + 12
        return f"https://servicos.aridesa.com.br/comentario/ita/2024/#gallery-{gid}-{slide}"
    if ano in (2022, 2023):
        gid = ITA_F2_GAL_2022_2023.get(sufixo, 6)
        return f"https://servicos.aridesa.com.br/comentario/ita/{ano}/#gallery-{gid}-{numero}"
    if 2019 <= ano <= 2021:
        # Sem deep-link: Aridesa usa a mesma landing page da 1ª fase
        return f"http://login.aridesa.com.br/vestibular/ita{ano}/index.aspx"
    return ""


def url_resolucao(fase: int, sufixo: str, vestibular: str, ano: int, numero: int) -> str:
    if fase == 2:
        return url_resolucao_fase2(sufixo, vestibular, ano, numero)
    return url_resolucao_fase1(sufixo, vestibular, ano, numero)


def build_materia(cfg: dict) -> dict:
    taxonomia = carregar_taxonomia(cfg["taxonomia"])
    prova_ids = descobrir_provas(cfg["sufixo"])
    todas = carregar_questoes(prova_ids)
    classificadas = [q for q in todas if q["status"].get("classificado")]

    sub_to_bloco: dict[str, str] = {}
    topic_names: dict[str, str] = {}
    for bloco in taxonomia["blocos"]:
        for sub in bloco.get("subareas", []):
            sub_to_bloco[sub["id"]] = bloco["id"]
            topic_names[sub["id"]] = sub["nome"]

    # Tags: uma questão aparece em TODAS as subáreas listadas em topicos_ids.
    por_sub: dict[str, list] = defaultdict(list)
    for q in classificadas:
        ids = q["classificacao"].get("topicos_ids", [])
        if not ids:
            continue
        for tid in dict.fromkeys(ids):  # preserva ordem, remove duplicatas
            por_sub[tid].append(q)

    blocos = []
    for bloco in taxonomia["blocos"]:
        subareas = []
        bloco_qids: set[str] = set()
        for sub in bloco.get("subareas", []):
            qs_sub = sorted(
                por_sub.get(sub["id"], []),
                key=lambda q: (q["prova"]["ano"], q.get("numero", 0)),
            )
            if not qs_sub:
                continue
            questoes_data = [
                {
                    "id": q.get("id", ""),
                    "vestibular": q["prova"].get("vestibular", "ITA"),
                    "ano": q["prova"]["ano"],
                    "fase": q["prova"].get("fase", 1),
                    "numero": q.get("numero", 0),
                    "topicos_ids": q["classificacao"].get("topicos_ids", []),
                    "gabarito": q.get("gabarito", "?"),
                    "img_src": q.get("imagem_questao_url", ""),
                    "usa_imagem": bool(q.get("usa_imagem_no_render") or q.get("imagem_questao_url")),
                    "enunciado_md": q.get("enunciado_md", ""),
                    "alternativas": q.get("alternativas", {}),
                    "obs": q["classificacao"].get("observacao", ""),
                    "resolucao_url": url_resolucao(
                        q["prova"].get("fase", 1),
                        cfg["sufixo"],
                        q["prova"].get("vestibular", "ITA"),
                        q["prova"]["ano"],
                        q.get("numero", 0),
                    ),
                }
                for q in qs_sub
            ]
            subareas.append({
                "id": sub["id"],
                "nome": sub["nome"],
                "questoes": questoes_data,
                "total": len(questoes_data),
            })
            for q in qs_sub:
                bloco_qids.add(q.get("id", ""))
        if subareas:
            blocos.append({
                "id": bloco["id"],
                "nome": bloco["nome"],
                "subareas": subareas,
                "total": len(bloco_qids),
            })

    anos = sorted(set(q["prova"]["ano"] for q in classificadas))
    fases = sorted(set(q["prova"].get("fase", 1) for q in classificadas))
    return {
        "nome": cfg["nome"],
        "cor": cfg["cor"],
        "cor_claro": cfg["cor_claro"],
        "total": len(classificadas),
        "anos": anos,
        "fases": fases,
        "blocos": blocos,
        "sub_to_bloco": sub_to_bloco,
        "topic_names": topic_names,
    }


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Banco ITA · IME — Física · Química · Matemática</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,500;0,9..144,600;1,9..144,400;1,9..144,500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/banco.css">
</head>
<body>

<div class="ita-logo-corner">
  <img src="https://ita-por-assunto.s3.us-east-1.amazonaws.com/imagens/logo-ita-branco.png" alt="ITA">
  <div class="sep"></div>
  <img src="https://ita-por-assunto.s3.us-east-1.amazonaws.com/imagens/logo-ime-branco.png" alt="IME">
</div>

<nav class="top-tabs" id="top-tabs">
  <button class="top-tab active" data-tab="banco" onclick="setTopTab('banco')">banco</button>
  <button class="top-tab" data-tab="estatisticas" onclick="setTopTab('estatisticas')">estatísticas</button>
</nav>

<div id="tab-banco" class="tab-panel active">
<div class="app">
  <aside class="sidebar">
    <div class="sb-brand">
      <div class="sb-brand-inner">
        <div class="logo">
          <img src="https://ita-por-assunto.s3.us-east-1.amazonaws.com/imagens/logo-ari-branco.png" alt="Ari de Sá">
        </div>
        <div>
          <div class="eyebrow">Colégio Ari de Sá</div>
          <div class="title">Banco <em>ITA · IME</em></div>
        </div>
      </div>
    </div>

    <div class="sb-meta">
      <div class="total"><span class="num" id="sb-total">—</span><span>questões no banco</span></div>
      <div class="updated" id="sb-updated">atualizado em __DATA_GERACAO__</div>
    </div>

    <div class="sb-toggle" id="vest-toggle">
      <button class="active" data-vest="all" onclick="setVestibular('all')">Todos</button>
      <button data-vest="ITA" onclick="setVestibular('ITA')">ITA</button>
      <button data-vest="IME" onclick="setVestibular('IME')">IME</button>
    </div>

    <div class="sb-section-label">Disciplinas</div>
    <div id="materia-list"></div>
  </aside>

  <main class="main" id="content">
    <div class="page-head">
      <div class="breadcrumb">
        <a onclick="setFilter('all')">banco</a>
        <span class="sep">›</span>
        <span id="bc-materia"></span>
      </div>
      <div class="page-title-row">
        <h1 id="content-title">Carregando…</h1>
        <div id="content-meta"></div>
      </div>
    </div>
    <div class="filter-bar" id="year-filter-bar"></div>
    <div class="filter-bar" id="fase-filter-bar"></div>
    <div id="questoes-container"></div>
  </main>
</div>
</div>

<div id="tab-estatisticas" class="tab-panel">
  <div class="stats-wrap" id="stats-wrap"></div>
</div>

<script id="banco-data" type="application/json">
__BANCO_DATA__
</script>

<script src="assets/banco.js" defer></script>
</body>
</html>
"""


def main():
    materias = [build_materia(cfg) for cfg in MATERIAS_CONFIG]
    total = sum(m["total"] for m in materias)
    data_geracao = datetime.now().strftime("%d/%m/%Y %H:%M")

    data_json = json.dumps(materias, ensure_ascii=False, separators=(",", ":"))

    html = (
        HTML_TEMPLATE
        .replace("__BANCO_DATA__", data_json)
        .replace("__DATA_GERACAO__", data_geracao)
    )

    DIR_OUTPUT.mkdir(exist_ok=True)
    output = DIR_OUTPUT / "banco_unificado.html"
    output.write_text(html, encoding="utf-8")
    print(f"✓ HTML gerado: {output}")
    for m in materias:
        print(f"  {m['nome']}: {m['total']} questões · {len(m['blocos'])} blocos")
    print(f"  Total: {total} questões")


if __name__ == "__main__":
    main()
