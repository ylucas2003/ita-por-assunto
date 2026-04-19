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

# IME reference_ids for comentarios.aridesa.com.br (no formula — hard-coded)
IME_REF_IDS = {2023: 3, 2024: 2, 2025: 4}


def url_resolucao_fase1(sufixo: str, vestibular: str, ano: int, numero: int) -> str:
    """Return the Aridesa resolution URL for a 1st-phase question, or '' if unknown."""
    if vestibular == "IME":
        if ano in IME_REF_IDS:
            return f"https://comentarios.aridesa.com.br/ime?reference_id={IME_REF_IDS[ano]}"
        if ano == 2022:
            return "https://servicos.aridesa.com.br/comentario/ime/2022-2023/"
        if ano == 2021:
            return "https://servicos.aridesa.com.br/comentario/ime/2021-2022/"
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


def build_materia(cfg: dict) -> dict:
    taxonomia = carregar_taxonomia(cfg["taxonomia"])
    prova_ids = descobrir_provas(cfg["sufixo"])
    todas = carregar_questoes(prova_ids)
    classificadas = [q for q in todas if q["status"].get("classificado")]

    por_sub: dict[str, list] = defaultdict(list)
    for q in classificadas:
        ids = q["classificacao"].get("topicos_ids", [])
        por_sub[ids[0] if ids else "?"].append(q)

    blocos = []
    for bloco in taxonomia["blocos"]:
        subareas = []
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
                    "numero": q.get("numero", 0),
                    "topicos_ids": q["classificacao"].get("topicos_ids", []),
                    "gabarito": q.get("gabarito", "?"),
                    "img_src": q.get("imagem_questao_url", ""),
                    "usa_imagem": bool(q.get("usa_imagem_no_render") or q.get("imagem_questao_url")),
                    "enunciado_md": q.get("enunciado_md", ""),
                    "alternativas": q.get("alternativas", {}),
                    "obs": q["classificacao"].get("observacao", ""),
                    "resolucao_url": url_resolucao_fase1(
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
        if subareas:
            blocos.append({
                "id": bloco["id"],
                "nome": bloco["nome"],
                "subareas": subareas,
                "total": sum(s["total"] for s in subareas),
            })

    anos = sorted(set(q["prova"]["ano"] for q in classificadas))
    return {
        "nome": cfg["nome"],
        "cor": cfg["cor"],
        "cor_claro": cfg["cor_claro"],
        "total": len(classificadas),
        "anos": anos,
        "blocos": blocos,
    }


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Banco ITA · IME — Física · Química · Matemática</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --ari-blue: #1a1b6e;
  --ari-blue-light: #f0eff9;
  --ime-purple: #4a1d4a;
  --ita-yellow: #FFC72C;
  --paper: #f5f4ef;
  --paper-dark: #e8e6de;
  --text-primary: #2c2c2a;
  --text-secondary: #5f5e5a;
  --text-tertiary: #888780;
  --border: #d3d1c7;
  --white: #ffffff;
}

html, body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: var(--paper);
  color: var(--text-primary);
  line-height: 1.5;
  height: 100%;
}

.mono { font-family: "SF Mono", Monaco, Consolas, monospace; }
button { font-family: inherit; cursor: pointer; border: none; background: none; }
a { color: inherit; text-decoration: none; }

/* ── LAYOUT ── */
.app {
  display: grid;
  grid-template-columns: 260px 1fr;
  min-height: 100vh;
}

/* ── SIDEBAR ── */
.sidebar {
  background: var(--white);
  border-right: 0.5px solid var(--border);
  padding: 1.75rem 1.25rem;
  position: sticky;
  top: 0;
  height: 100vh;
  overflow-y: auto;
}
.sidebar::-webkit-scrollbar { width: 4px; }
.sidebar::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

.sb-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 1.25rem;
  padding-bottom: 1.25rem;
  border-bottom: 0.5px solid var(--border);
}
.sb-brand .logo {
  width: 32px; height: 32px;
  background: var(--ari-blue);
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.sb-brand .eyebrow {
  font-size: 9px;
  letter-spacing: 0.18em;
  color: var(--text-tertiary);
  text-transform: uppercase;
  margin-bottom: 2px;
}
.sb-brand .title {
  font-size: 13px;
  color: var(--ari-blue);
  font-weight: 500;
}

.sb-meta {
  margin-bottom: 1.25rem;
  padding: 0 4px;
}
.sb-meta .total {
  font-size: 11px;
  color: var(--text-tertiary);
  letter-spacing: 0.06em;
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.sb-meta .total .num {
  font-size: 18px;
  color: var(--ari-blue);
  font-weight: 500;
  font-family: "SF Mono", Monaco, Consolas, monospace;
  letter-spacing: 0;
}
.sb-meta .updated {
  font-size: 10px;
  color: var(--text-tertiary);
  margin-top: 4px;
}

.sb-toggle {
  display: flex;
  gap: 3px;
  background: var(--paper);
  border-radius: 3px;
  padding: 3px;
  margin-bottom: 1.25rem;
}
.sb-toggle button {
  flex: 1;
  padding: 7px 0;
  font-size: 11px;
  color: var(--text-secondary);
  border-radius: 2px;
  letter-spacing: 0.04em;
  transition: all 0.15s;
}
.sb-toggle button.active {
  background: var(--white);
  color: var(--ari-blue);
  font-weight: 500;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}

.sb-section-label {
  font-size: 10px;
  letter-spacing: 0.12em;
  color: var(--text-tertiary);
  text-transform: uppercase;
  margin-bottom: 10px;
  padding: 0 4px;
}

.sb-discipline {
  padding: 10px 12px;
  border-radius: 4px;
  margin-bottom: 2px;
  cursor: pointer;
  transition: background 0.15s;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.sb-discipline:hover { background: var(--paper); }
.sb-discipline.active { background: var(--ari-blue); }
.sb-discipline.active .sb-disc-name { color: var(--white); font-weight: 500; }
.sb-discipline.active .sb-disc-count { color: rgba(255,255,255,0.6); }
.sb-disc-name { font-size: 13px; color: var(--text-primary); }
.sb-disc-count { font-size: 11px; color: var(--text-tertiary); font-family: "SF Mono", Monaco, Consolas, monospace; }

.sb-subtopics {
  display: none;
  padding-left: 12px;
  margin: 4px 0 12px;
  border-left: 0.5px solid var(--border);
  margin-left: 16px;
}
.sb-subtopics.open { display: block; }

.sb-bloco-label {
  padding: 6px 10px 2px;
  font-size: 10px;
  letter-spacing: 0.1em;
  color: var(--text-tertiary);
  text-transform: uppercase;
}

.sb-subtopic {
  padding: 6px 10px;
  font-size: 12px;
  color: var(--text-secondary);
  border-radius: 3px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  transition: all 0.15s;
  gap: 6px;
}
.sb-subtopic:hover { background: var(--paper); color: var(--text-primary); }
.sb-subtopic.active { color: var(--ari-blue); font-weight: 500; }
.sb-subtopic.active::before {
  content: '';
  display: block;
  width: 3px; height: 14px;
  background: var(--ita-yellow);
  margin-right: 4px;
  margin-left: -13px;
  border-radius: 1px;
  flex-shrink: 0;
}
.sb-subtopic .sc { font-size: 10px; color: var(--text-tertiary); font-family: "SF Mono", Monaco, Consolas, monospace; flex-shrink: 0; }

/* ── MAIN ── */
.main {
  padding: 2.25rem 2.75rem 4rem;
}

.page-head {
  margin-bottom: 1.5rem;
  padding-bottom: 1.25rem;
  border-bottom: 0.5px solid var(--border);
}
.breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: var(--text-tertiary);
  margin-bottom: 14px;
  letter-spacing: 0.02em;
}
.breadcrumb a { color: var(--ari-blue); cursor: pointer; }
.breadcrumb a:hover { text-decoration: underline; }
.breadcrumb .sep { opacity: 0.4; }
.page-title-row h1 {
  font-size: 24px;
  color: var(--ari-blue);
  font-weight: 500;
  letter-spacing: -0.015em;
  line-height: 1.15;
}
#content-meta {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 6px;
  letter-spacing: 0.02em;
}

/* ── FILTER BAR ── */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}
.filter-label {
  font-size: 11px;
  color: var(--text-tertiary);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  margin-right: 2px;
}
.chip {
  padding: 5px 11px;
  background: var(--white);
  border: 0.5px solid var(--border);
  border-radius: 20px;
  font-size: 11.5px;
  color: var(--text-primary);
  cursor: pointer;
  transition: all 0.15s;
  font-family: inherit;
}
.chip:hover { border-color: var(--ari-blue); color: var(--ari-blue); }
.chip.active { background: var(--ari-blue); color: var(--white); border-color: var(--ari-blue); font-weight: 500; }

/* ── TOPIC ── */
.topic { margin-bottom: 2rem; }
.topic-head {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 1rem;
  padding-bottom: 10px;
  border-bottom: 0.5px solid var(--border);
}
.topic-head .num {
  font-size: 11px;
  letter-spacing: 0.2em;
  color: var(--ari-blue);
  font-weight: 500;
  padding: 3px 10px;
  background: var(--ari-blue-light);
  border-radius: 3px;
  font-family: "SF Mono", Monaco, Consolas, monospace;
}
.topic-head .name { font-size: 15px; color: var(--text-primary); font-weight: 500; }
.topic-head .rule { flex: 1; }
.topic-head .tc { font-size: 11px; color: var(--text-tertiary); letter-spacing: 0.04em; }

/* ── QUESTION CARD ── */
.question {
  background: var(--white);
  border-radius: 4px;
  margin-bottom: 14px;
  overflow: hidden;
  border-left: 3px solid var(--ari-blue);
  transition: box-shadow 0.15s;
}
.question.ime { border-left-color: var(--ime-purple); }
.question:hover { box-shadow: 0 2px 12px rgba(26,27,110,0.08); }

.question-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 18px;
  border-bottom: 0.5px solid var(--paper-dark);
  flex-wrap: wrap;
}
.q-inst {
  padding: 3px 9px;
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.12em;
  color: var(--white);
  border-radius: 2px;
}
.q-inst.ita { background: var(--ari-blue); }
.q-inst.ime { background: var(--ime-purple); }
.q-year { font-size: 13px; color: var(--text-primary); font-weight: 500; letter-spacing: 0.02em; }
.q-num { font-size: 11px; color: var(--text-tertiary); letter-spacing: 0.04em; }
.q-topic-tag {
  font-size: 10px;
  color: var(--text-secondary);
  padding: 3px 8px;
  background: var(--paper);
  border-radius: 2px;
  letter-spacing: 0.04em;
}
.q-spacer { flex: 1; }
.q-answer {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--text-tertiary);
  letter-spacing: 0.04em;
}
.q-answer .letter {
  display: inline-block;
  width: 20px; height: 20px;
  line-height: 20px;
  text-align: center;
  background: var(--ari-blue);
  color: var(--white);
  border-radius: 50%;
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0;
}
.question.ime .q-answer .letter { background: var(--ime-purple); }
.q-action-btn {
  padding: 5px 11px;
  font-size: 11px;
  color: var(--ari-blue);
  background: transparent;
  border: 0.5px solid var(--border);
  border-radius: 3px;
  letter-spacing: 0.02em;
  transition: all 0.15s;
  cursor: pointer;
  font-family: inherit;
  white-space: nowrap;
}
.q-action-btn:hover { border-color: var(--ari-blue); background: var(--ari-blue-light); }

.question-body { padding: 18px 22px 14px; }
.question-statement {
  background: var(--paper);
  border-radius: 3px;
  padding: 16px 20px;
  font-family: Georgia, serif;
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-primary);
  white-space: pre-wrap;
}
.question-statement img { max-width: 100%; height: auto; display: block; margin: 0.5em 0; }

.question-caption {
  padding: 10px 22px 14px;
  font-size: 11.5px;
  font-style: italic;
  color: var(--text-secondary);
  line-height: 1.5;
  border-top: 0.5px solid var(--paper-dark);
}
.question-caption::before { content: '❝ '; color: var(--ari-blue); font-style: normal; margin-right: 4px; }

.empty-state { text-align: center; padding: 4rem 0; color: var(--text-tertiary); font-size: 13px; }

.ita-logo-corner {
  position: fixed;
  top: 18px;
  right: 22px;
  z-index: 100;
  opacity: 0.82;
  transition: opacity 0.2s;
}
.ita-logo-corner:hover { opacity: 1; }
.ita-logo-corner img { height: 48px; width: auto; display: block; }
</style>
</head>
<body>

<div class="ita-logo-corner">
  <img src="https://ita-por-assunto.s3.us-east-1.amazonaws.com/imagens/logo-ita.png" alt="ITA">
</div>

<div class="app">
  <aside class="sidebar">
    <div class="sb-brand">
      <div class="logo">
        <svg viewBox="0 0 40 40" width="20" height="20">
          <path d="M 12 28 L 20 10 L 28 28 M 15.5 22 L 24.5 22" fill="none" stroke="#ffffff" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>
      <div>
        <div class="eyebrow">Colégio Ari de Sá</div>
        <div class="title">Banco ITA · IME</div>
      </div>
    </div>

    <div class="sb-meta">
      <div class="total"><span class="num" id="sb-total">—</span><span>questões no banco</span></div>
      <div class="updated" id="sb-updated"></div>
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
    <div id="questoes-container"></div>
  </main>
</div>

<script id="banco-data" type="application/json">
__BANCO_DATA__
</script>

<script>
const DATA = JSON.parse(document.getElementById('banco-data').textContent);

const state = {
  materia: DATA[0].nome,
  filter: 'all',
  vestibular: 'all',
  ano: 'all',
};

function getM(nome) { return DATA.find(m => m.nome === nome); }

// ── SIDEBAR ───────────────────────────────────────────────────────────

function renderMateriaList() {
  const cont = document.getElementById('materia-list');
  cont.innerHTML = DATA.map(m => {
    const isActive = m.nome === state.materia;
    const subtopics = isActive ? m.blocos.map(bloco =>
      `<div class="sb-bloco-label">${bloco.nome}</div>` +
      bloco.subareas.map(sub => {
        const f = `sub:${sub.id}`;
        return `<div class="sb-subtopic ${state.filter === f ? 'active' : ''}" onclick="setFilter('${f}')">
          <span>${sub.id} ${sub.nome}</span>
          <span class="sc">${sub.total}</span>
        </div>`;
      }).join('')
    ).join('') : '';
    return `
      <div class="sb-discipline ${isActive ? 'active' : ''}" onclick="setMateria('${m.nome}')">
        <span class="sb-disc-name">${m.nome}</span>
        <span class="sb-disc-count">${m.total}</span>
      </div>
      <div class="sb-subtopics ${isActive ? 'open' : ''}">${subtopics}</div>`;
  }).join('');
}

// ── YEAR FILTER ───────────────────────────────────────────────────────

function renderYearFilter() {
  const m = getM(state.materia);
  const bar = document.getElementById('year-filter-bar');
  bar.innerHTML = `
    <span class="filter-label">ano</span>
    <button class="chip ${state.ano === 'all' ? 'active' : ''}" onclick="setAno('all')">todos</button>
    ${m.anos.map(a => `<button class="chip ${state.ano === a ? 'active' : ''}" onclick="setAno(${a})">${a}</button>`).join('')}`;
}

function setAno(ano) {
  state.ano = ano;
  renderYearFilter();
  renderContent();
  document.getElementById('content').scrollTop = 0;
}

// ── CONTENT ───────────────────────────────────────────────────────────

function renderQuestion(q) {
  const vest = q.vestibular || 'ITA';
  const vestCls = vest.toLowerCase();
  let stmtHtml;
  if (q.usa_imagem && q.img_src) {
    stmtHtml = `<img src="${q.img_src}" alt="Q${q.numero}" loading="lazy">`;
  } else {
    const enc = (q.enunciado_md || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    stmtHtml = enc;
  }
  const topicTag = q.topicos_ids.length
    ? `<span class="q-topic-tag">${q.topicos_ids[0]}</span>` : '';
  const resBtn = q.resolucao_url
    ? `<a class="q-action-btn" href="${q.resolucao_url}" target="_blank" rel="noopener">resolução ↗</a>`
    : '';
  const caption = q.obs
    ? `<div class="question-caption">${q.obs.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}</div>`
    : '';
  return `
    <article class="question ${vestCls}" data-vest="${vest}" data-ano="${q.ano}">
      <div class="question-head">
        <span class="q-inst ${vestCls}">${vest}</span>
        <span class="q-year">${q.ano}</span>
        <span class="q-num">Questão ${q.numero}</span>
        ${topicTag}
        <div class="q-spacer"></div>
        <div class="q-answer">resp. <span class="letter">${q.gabarito}</span></div>
        ${resBtn}
      </div>
      <div class="question-body">
        <div class="question-statement">${stmtHtml}</div>
      </div>
      ${caption}
    </article>`;
}

function renderContent() {
  const m = getM(state.materia);
  const f = state.filter;
  const cont = document.getElementById('questoes-container');

  let html = '';
  let shown = 0;

  for (const bloco of m.blocos) {
    const showBloco = f === 'all' || (f.startsWith('sub:') && f.slice(4).startsWith(bloco.id + '.'));
    if (!showBloco) continue;

    for (const sub of bloco.subareas) {
      const subFilter = `sub:${sub.id}`;
      if (f !== 'all' && f !== subFilter) continue;
      let qsFilt = state.vestibular === 'all'
        ? sub.questoes
        : sub.questoes.filter(q => (q.vestibular || 'ITA') === state.vestibular);
      if (state.ano !== 'all') qsFilt = qsFilt.filter(q => q.ano === state.ano);
      if (!qsFilt.length) continue;
      html += `
        <div class="topic">
          <div class="topic-head">
            <span class="num">${sub.id}</span>
            <span class="name">${sub.nome}</span>
            <span class="rule"></span>
            <span class="tc">${qsFilt.length} questões</span>
          </div>
          ${qsFilt.map(q => renderQuestion(q)).join('')}
        </div>`;
      shown += qsFilt.length;
    }
  }

  cont.innerHTML = html || '<div class="empty-state">Nenhuma questão encontrada.</div>';

  const titleEl = document.getElementById('content-title');
  const metaEl = document.getElementById('content-meta');
  document.getElementById('bc-materia').textContent = m.nome.toLowerCase();

  if (f === 'all') {
    titleEl.textContent = m.nome;
    metaEl.textContent = `${m.total} questões · anos: ${m.anos.join(', ')}`;
  } else if (f.startsWith('sub:')) {
    const sid = f.slice(4);
    const bloco = m.blocos.find(b => b.subareas.some(s => s.id === sid));
    const sub = bloco?.subareas.find(s => s.id === sid);
    titleEl.textContent = sub ? sub.nome : m.nome;
    metaEl.textContent = `${shown} questões`;
  }
}

// ── NAVIGATION ────────────────────────────────────────────────────────

function setMateria(nome) {
  state.materia = nome;
  state.filter = 'all';
  state.ano = 'all';
  renderMateriaList();
  renderYearFilter();
  renderContent();
  document.getElementById('content').scrollTop = 0;
}

function setVestibular(vest) {
  state.vestibular = vest;
  document.querySelectorAll('#vest-toggle button').forEach(el => {
    el.classList.toggle('active', el.dataset.vest === vest);
  });
  renderContent();
  document.getElementById('content').scrollTop = 0;
}

function setFilter(f) {
  state.filter = f;
  state.ano = 'all';
  renderMateriaList();
  renderYearFilter();
  renderContent();
  document.getElementById('content').scrollTop = 0;
}

// ── INIT ──────────────────────────────────────────────────────────────

const total = DATA.reduce((s, m) => s + m.total, 0);
document.getElementById('sb-total').textContent = total;
document.getElementById('sb-updated').textContent = 'atualizado em __DATA_GERACAO__';

renderMateriaList();
renderYearFilter();
renderContent();
</script>
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
