const DATA = JSON.parse(document.getElementById('banco-data').textContent);

const state = {
  materia: DATA[0].nome,
  expanded: DATA[0].nome,
  openBlocos: {},
  filter: 'all',
  vestibular: 'all',
  ano: 'all',
  fase: 'all',
};

function getM(nome) { return DATA.find(m => m.nome === nome); }

// ── SIDEBAR ───────────────────────────────────────────────────────────

function blocoKey(materia, bloco) { return materia + '::' + bloco; }

function matIcon(nome) {
  const n = (nome || '').toLowerCase();
  const base = '<svg class="sb-disc-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">';
  if (n.startsWith('fís') || n.startsWith('fis')) {
    return base + '<circle cx="12" cy="12" r="1.5" fill="currentColor"/><ellipse cx="12" cy="12" rx="10" ry="4.5"/><ellipse cx="12" cy="12" rx="10" ry="4.5" transform="rotate(60 12 12)"/><ellipse cx="12" cy="12" rx="10" ry="4.5" transform="rotate(120 12 12)"/></svg>';
  }
  if (n.startsWith('quím') || n.startsWith('quim')) {
    return base + '<path d="M9 3h6"/><path d="M10 3v6.5L4.5 19a1.5 1.5 0 0 0 1.3 2.25h12.4A1.5 1.5 0 0 0 19.5 19L14 9.5V3"/><path d="M7 15h10"/></svg>';
  }
  if (n.startsWith('mat')) {
    return base + '<path d="M3 13l3.5 3.5L11 6h10"/></svg>';
  }
  return '';
}

function renderMateriaList() {
  const cont = document.getElementById('materia-list');
  cont.innerHTML = DATA.map(m => {
    const isActive = m.nome === state.materia;
    const isExpanded = m.nome === state.expanded;
    const subtopics = isExpanded ? m.blocos.map((bloco, bi) => {
      const k = blocoKey(m.nome, bloco.nome);
      const blocoOpen = !!state.openBlocos[k];
      const blocoActive = isActive && state.filter === `bloco:${bloco.id}`;
      const subs = blocoOpen ? bloco.subareas.map(sub => {
        const f = `sub:${sub.id}`;
        return `<div class="sb-subtopic ${state.filter === f && isActive ? 'active' : ''}" onclick="setFilter('${f}','${m.nome}')">
          <span>${sub.id} ${sub.nome}</span>
          <span class="sc">${sub.total}</span>
        </div>`;
      }).join('') : '';
      return `
        <div class="sb-bloco-label ${blocoOpen ? 'open' : ''} ${blocoActive ? 'active' : ''}" onclick="toggleBloco('${m.nome.replace(/'/g, "\\'")}', ${bi})">
          <span>${bloco.nome}</span>
          <svg class="chev" width="9" height="9" viewBox="0 0 10 10"><path d="M 2 3.5 L 5 6.5 L 8 3.5" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </div>
        <div class="sb-bloco-subs ${blocoOpen ? 'open' : ''}">${subs}</div>`;
    }).join('') : '';
    return `
      <div class="sb-discipline ${isActive ? 'active' : ''}" onclick="setMateria('${m.nome}')">
        <span class="sb-disc-left">${matIcon(m.nome)}<span class="sb-disc-name">${m.nome}</span></span>
        <span class="sb-disc-count">${m.total}</span>
      </div>
      <div class="sb-subtopics ${isExpanded ? 'open' : ''}">${subtopics}</div>`;
  }).join('');
}

function toggleBloco(materiaNome, blocoIdx) {
  const m = getM(materiaNome);
  if (!m) return;
  const bloco = m.blocos[blocoIdx];
  if (!bloco) return;

  if (state.materia !== materiaNome) {
    state.materia = materiaNome;
    state.expanded = materiaNome;
  }

  const k = blocoKey(materiaNome, bloco.nome);
  const wasOpen = !!state.openBlocos[k];
  const f = state.filter;
  const belongsToBloco = f === `bloco:${bloco.id}` || (f.startsWith('sub:') && f.slice(4).startsWith(bloco.id + '.'));

  if (wasOpen) {
    state.openBlocos[k] = false;
    if (belongsToBloco) {
      state.filter = 'all';
      state.ano = 'all';
      state.fase = 'all';
    }
  } else {
    state.openBlocos[k] = true;
    state.filter = `bloco:${bloco.id}`;
    state.ano = 'all';
    state.fase = 'all';
  }

  renderMateriaList();
  renderYearFilter();
  renderFaseFilter();
  renderContent();
  document.getElementById('content').scrollTop = 0;
}

// ── YEAR FILTER ───────────────────────────────────────────────────────

function renderYearFilter() {
  const m = getM(state.materia);
  const bar = document.getElementById('year-filter-bar');
  bar.innerHTML = `
    <button class="chip ${state.ano === 'all' ? 'active' : ''}" onclick="setAno('all')">todos</button>
    ${m.anos.map(a => `<button class="chip ${state.ano === a ? 'active' : ''}" onclick="setAno(${a})">${a}</button>`).join('')}`;
}

function setAno(ano) {
  state.ano = ano;
  renderYearFilter();
  renderContent();
  document.getElementById('content').scrollTop = 0;
}

// ── FASE FILTER ───────────────────────────────────────────────────────

function renderFaseFilter() {
  const m = getM(state.materia);
  const bar = document.getElementById('fase-filter-bar');
  const label = document.getElementById('fase-section-label');
  if (!m.fases || m.fases.length < 2) {
    bar.innerHTML = '';
    bar.style.display = 'none';
    if (label) label.style.display = 'none';
    return;
  }
  bar.style.display = '';
  if (label) label.style.display = '';
  bar.innerHTML = `
    <button class="chip ${state.fase === 'all' ? 'active' : ''}" onclick="setFase('all')">todas</button>
    ${m.fases.map(f => `<button class="chip ${state.fase === f ? 'active' : ''}" onclick="setFase(${f})">${f}ª</button>`).join('')}`;
}

function setFase(fase) {
  state.fase = fase;
  renderFaseFilter();
  renderContent();
  document.getElementById('content').scrollTop = 0;
}

// ── CONTENT ───────────────────────────────────────────────────────────

// ── HELPERS DE PERSISTÊNCIA LOCAL ────────────────────────────────
const LS_RESOLVED = 'banco-resolved';
const LS_NOTES = 'banco-notes';

function _lsLoadSet(k) { try { return new Set(JSON.parse(localStorage.getItem(k) || '[]')); } catch { return new Set(); } }
function _lsSaveSet(k, s) { try { localStorage.setItem(k, JSON.stringify([...s])); } catch {} }
function _lsLoadMap(k) { try { return JSON.parse(localStorage.getItem(k) || '{}'); } catch { return {}; } }
function _lsSaveMap(k, m) { try { localStorage.setItem(k, JSON.stringify(m)); } catch {} }

let resolvedSet = _lsLoadSet(LS_RESOLVED);
let notesMap = _lsLoadMap(LS_NOTES);

function isResolved(qid) { return resolvedSet.has(qid); }
function toggleResolved(qid, btn) {
  if (resolvedSet.has(qid)) {
    resolvedSet.delete(qid);
    btn.classList.remove('done');
    const label = btn.querySelector('.qp-mark-label');
    if (label) label.textContent = 'Marcar como resolvida';
  } else {
    resolvedSet.add(qid);
    btn.classList.add('done');
    const label = btn.querySelector('.qp-mark-label');
    if (label) label.textContent = 'Resolvida';
  }
  _lsSaveSet(LS_RESOLVED, resolvedSet);
}
function getNote(qid) { return notesMap[qid] || ''; }
function saveNote(qid, v) {
  if (v) notesMap[qid] = v; else delete notesMap[qid];
  _lsSaveMap(LS_NOTES, notesMap);
}

function _esc(s) {
  return (s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── LUCIDE-STYLE SVG ICONS ───────────────────────────────────────
function lu(name) {
  const p = {
    calendar: '<rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>',
    building: '<rect x="4" y="2" width="16" height="20" rx="2" ry="2"/><path d="M9 22v-4h6v4"/><path d="M8 6h.01M16 6h.01M12 6h.01M12 10h.01M8 10h.01M16 10h.01M12 14h.01M8 14h.01M16 14h.01"/>',
    clipboard: '<rect x="8" y="2" width="8" height="4" rx="1" ry="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>',
    hash: '<line x1="4" y1="9" x2="20" y2="9"/><line x1="4" y1="15" x2="20" y2="15"/><line x1="10" y1="3" x2="8" y2="21"/><line x1="16" y1="3" x2="14" y2="21"/>',
    book: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
    checkCircle: '<circle cx="12" cy="12" r="10"/><polyline points="9 12 12 15 17 9"/>',
    edit: '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>',
    arrowUpRight: '<line x1="7" y1="17" x2="17" y2="7"/><polyline points="7 7 17 7 17 17"/>',
    bookmark: '<path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>',
    moreH: '<circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/>'
  };
  return `<svg class="lu" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${p[name] || ''}</svg>`;
}

function renderQuestion(q, m) {
  const vest = q.vestibular || 'ITA';
  const vestCls = vest.toLowerCase();
  let stmtHtml;
  if (q.usa_imagem && q.img_src) {
    stmtHtml = `<img src="${q.img_src}" alt="Q${q.numero}" loading="lazy">`;
  } else {
    stmtHtml = _esc(q.enunciado_md || '');
  }
  const ids = q.topicos_ids || [];
  const materiaEsc = m.nome.replace(/'/g, "\\'");

  // Tópico primário — pill navy-50
  const primaryId = ids[0] || '';
  const primaryName = primaryId ? ((m.topic_names && m.topic_names[primaryId]) || '') : '';
  const topicPill = primaryId
    ? `<span class="qp-topic-pill" title="${_esc(primaryName)}" onclick="setFilter('sub:${primaryId}','${materiaEsc}')"><span class="dot"></span>${primaryId} ${_esc(primaryName)}</span>`
    : `<span class="qp-topic-pill empty"><span class="dot"></span>sem tópico</span>`;
  const extraTopics = ids.length > 1
    ? `<div class="qp-topic-extras">${ids.slice(1).map(tid => {
        const nome = (m.topic_names && m.topic_names[tid]) || '';
        return `<span class="qp-topic-pill extra" title="${_esc(nome)}" onclick="setFilter('sub:${tid}','${materiaEsc}')">${tid}${nome ? ' · ' + _esc(nome) : ''}</span>`;
      }).join('')}</div>`
    : '';

  // Informações
  const prova = q.fase ? `${q.fase}ª fase` : 'Objetiva';
  const infoRows = [
    ['calendar', 'Ano', q.ano],
    ['building', 'Instituição', vest],
    ['clipboard', 'Prova', prova],
    ['hash', 'Questão', q.numero],
    ['book', 'Disciplina', m.nome],
  ];
  const infoHtml = infoRows.map(([ic, k, v]) => `
    <div class="qp-info-row">
      <span class="qp-info-icon">${lu(ic)}</span>
      <span class="qp-info-key">${k}</span>
      <span class="qp-info-val">${_esc(String(v))}</span>
    </div>`).join('');

  // Gabarito (caixa grande)
  const gabBox = q.gabarito
    ? `<button class="q-gab-btn ${vestCls}" onclick="toggleGabarito(this)" data-gab="${q.gabarito}" type="button" aria-label="Revelar gabarito">
        <span class="gab-letter">${q.gabarito}</span>
      </button>`
    : `<div class="q-gab-btn disabled" aria-label="Sem gabarito"><span class="gab-letter">—</span></div>`;

  // Marcar como resolvida
  const isDone = isResolved(q.id);
  const markBtn = `<button class="qp-mark${isDone ? ' done' : ''}" data-qid="${_esc(q.id)}" onclick="toggleResolved('${_esc(q.id)}', this)" type="button">
      ${lu('checkCircle')}
      <span class="qp-mark-label">${isDone ? 'Resolvida' : 'Marcar como resolvida'}</span>
    </button>`;

  // Anotações
  const noteText = getNote(q.id);
  const notesTA = `<textarea class="qp-note" data-qid="${_esc(q.id)}" placeholder="Adicione uma anotação pessoal sobre esta questão…" oninput="saveNote('${_esc(q.id)}', this.value)">${_esc(noteText)}</textarea>`;

  // Resolução externa (opcional)
  const resBtn = q.resolucao_url
    ? `<a class="qp-link" href="${q.resolucao_url}" target="_blank" rel="noopener">ver resolução ${lu('arrowUpRight')}</a>`
    : '';

  // Caption
  const caption = q.obs
    ? `<div class="question-caption">${_esc(q.obs)}</div>`
    : '';

  return `
    <article class="question ${vestCls}" data-vest="${vest}" data-ano="${q.ano}">
      <div class="q-card">
        <div class="question-head">
          <span class="q-inst ${vestCls}">${vest}</span>
          <span class="q-year">${q.ano}</span>
          <span class="q-sep">·</span>
          <span class="q-num">Questão ${q.numero}</span>
          <span class="q-head-rule"></span>
          <button class="q-head-act" type="button" aria-label="Salvar questão" tabindex="-1">${lu('bookmark')}</button>
          <button class="q-head-act" type="button" aria-label="Mais opções" tabindex="-1">${lu('moreH')}</button>
        </div>
        <div class="question-main">
          <div class="question-statement">${stmtHtml}</div>
          ${caption}
        </div>
      </div>
      <aside class="question-side">
        <div class="qp-section qp-gab-section">
          <div class="qp-label">Gabarito</div>
          <div class="qp-sublabel">Alternativa correta</div>
          ${gabBox}
        </div>
        ${markBtn}
        <div class="qp-section qp-topico">
          <div class="qp-label">Tópico</div>
          ${topicPill}
          ${extraTopics}
        </div>
        <div class="qp-section qp-info">
          <div class="qp-label">Informações</div>
          <div class="qp-info-list">${infoHtml}</div>
        </div>
        <div class="qp-section qp-notes">
          <div class="qp-label">${lu('edit')}<span>Minhas anotações</span></div>
          ${notesTA}
        </div>
        ${resBtn}
      </aside>
    </article>`;
}

function toggleGabarito(btn) {
  btn.classList.toggle('revealed');
}

function scopePrimary(q, scopeBlocoId, subToBloco) {
  for (const tid of q.topicos_ids || []) {
    if (scopeBlocoId === null || subToBloco[tid] === scopeBlocoId) return tid;
  }
  return null;
}

function renderContent() {
  const m = getM(state.materia);
  const f = state.filter;
  const cont = document.getElementById('questoes-container');
  const isSubFilter = f.startsWith('sub:');
  const scopeBlocoId = f.startsWith('bloco:') ? f.slice(6) : null;

  let html = '';
  let shown = 0;

  for (const bloco of m.blocos) {
    const blocoFilter = `bloco:${bloco.id}`;
    const showBloco = f === 'all'
      || f === blocoFilter
      || (f.startsWith('sub:') && f.slice(4).startsWith(bloco.id + '.'));
    if (!showBloco) continue;

    for (const sub of bloco.subareas) {
      const subFilter = `sub:${sub.id}`;
      if (f !== 'all' && f !== subFilter && f !== blocoFilter) continue;
      let qsFilt = sub.questoes;
      if (!isSubFilter) {
        qsFilt = qsFilt.filter(q => scopePrimary(q, scopeBlocoId, m.sub_to_bloco) === sub.id);
      }
      if (state.vestibular !== 'all') qsFilt = qsFilt.filter(q => (q.vestibular || 'ITA') === state.vestibular);
      if (state.ano !== 'all') qsFilt = qsFilt.filter(q => q.ano === state.ano);
      if (state.fase !== 'all') qsFilt = qsFilt.filter(q => (q.fase || 1) === state.fase);
      if (!qsFilt.length) continue;
      html += `
        <div class="topic">
          <div class="topic-head">
            <span class="num">${sub.id}</span>
            <span class="name">${sub.nome}</span>
            <span class="rule"></span>
            <span class="tc">${qsFilt.length} questões</span>
          </div>
          ${qsFilt.map(q => renderQuestion(q, m)).join('')}
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
  } else if (f.startsWith('bloco:')) {
    const bid = f.slice(6);
    const bloco = m.blocos.find(b => b.id === bid);
    titleEl.textContent = bloco ? bloco.nome : m.nome;
    metaEl.textContent = `${shown} questões`;
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
  if (state.materia === nome) {
    state.expanded = (state.expanded === nome) ? null : nome;
    renderMateriaList();
    return;
  }
  state.materia = nome;
  state.expanded = nome;
  state.filter = 'all';
  state.ano = 'all';
  state.fase = 'all';
  renderMateriaList();
  renderYearFilter();
  renderFaseFilter();
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

function setFilter(f, materiaNome) {
  if (materiaNome && materiaNome !== state.materia) {
    state.materia = materiaNome;
    state.expanded = materiaNome;
  }
  state.filter = f;
  state.ano = 'all';
  state.fase = 'all';
  renderMateriaList();
  renderYearFilter();
  renderFaseFilter();
  renderContent();
  document.getElementById('content').scrollTop = 0;
}

// ── TOP TABS ──────────────────────────────────────────────────────────

function setTopTab(tab) {
  document.querySelectorAll('.top-tab').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.toggle('active', p.id === 'tab-' + tab));
  if (tab === 'estatisticas') buildStatsUI();
  if (tab === 'lista' && typeof buildListaUI === 'function') buildListaUI();
  if (tab === 'mensagem') {
    const quotes = document.querySelectorAll('#tab-mensagem .msg-quote');
    quotes.forEach(q => {
      q.classList.remove('animate-in');
      q.style.transitionDelay = '';
    });
    // força reflow para reiniciar a transição mesmo se já estavam visíveis
    if (quotes.length) void quotes[0].offsetWidth;
    requestAnimationFrame(() => {
      quotes.forEach((q, i) => {
        q.style.transitionDelay = (i * 140) + 'ms';
        q.classList.add('animate-in');
      });
    });
  }
}

window.DATA = DATA;

// ── ESTATÍSTICAS ──────────────────────────────────────────────────────

const statsState = {};
const statsCharts = {};

function statsSlug(nome) {
  return nome.toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-');
}

function statsVestibulares(m) {
  const set = new Set();
  for (const b of m.blocos) for (const s of b.subareas) for (const q of s.questoes) set.add(q.vestibular || 'ITA');
  return [...set].sort();
}

function aggregateStats(m, f) {
  const match = q => (f.vestibular === 'all' || (q.vestibular || 'ITA') === f.vestibular)
                  && (f.ano === 'all' || q.ano === f.ano)
                  && (f.fase === 'all' || (q.fase || 1) === f.fase);

  // Questões únicas que casam com o filtro (base para %) e soma de tags (marcações)
  const matched = new Set();
  let totalTags = 0;
  let multiTagQ = 0;
  for (const bloco of m.blocos) {
    for (const sub of bloco.subareas) {
      for (const q of sub.questoes) {
        if (match(q)) matched.add(q.id);
      }
    }
  }
  // Contagem de tags: itera questões únicas e soma topicos_ids
  const countedIds = new Set();
  for (const bloco of m.blocos) {
    for (const sub of bloco.subareas) {
      for (const q of sub.questoes) {
        if (!match(q) || countedIds.has(q.id)) continue;
        countedIds.add(q.id);
        const n = (q.topicos_ids || []).length || 1;
        totalTags += n;
        if (n > 1) multiTagQ++;
      }
    }
  }
  const total = matched.size;

  const subs = [];
  for (const bloco of m.blocos) {
    for (const sub of bloco.subareas) {
      const count = sub.questoes.filter(match).length;
      if (count === 0) continue;
      subs.push({ id: sub.id, nome: sub.nome, count, pct: total ? (count / total) * 100 : 0 });
    }
  }
  subs.sort((a, b) => b.pct - a.pct || a.id.localeCompare(b.id));
  return { subs, total, totalTags, multiTagQ };
}

function renderStatsFilters(m) {
  const slug = statsSlug(m.nome);
  const cur = statsState[m.nome];
  const nomeEsc = m.nome.replace(/'/g, "\\'");

  const vests = statsVestibulares(m);
  const vestBar = document.getElementById('stats-vest-' + slug);
  vestBar.innerHTML = vests.length > 1 ? `
    <span class="filter-label">vestibular</span>
    <button class="chip ${cur.vestibular === 'all' ? 'active' : ''}" onclick="setStatsFilter('${nomeEsc}','vestibular','all')">todos</button>
    ${vests.map(v => `<button class="chip ${cur.vestibular === v ? 'active' : ''}" onclick="setStatsFilter('${nomeEsc}','vestibular','${v}')">${v}</button>`).join('')}` : '';

  const yearBar = document.getElementById('stats-year-' + slug);
  yearBar.innerHTML = `
    <span class="filter-label">ano</span>
    <button class="chip ${cur.ano === 'all' ? 'active' : ''}" onclick="setStatsFilter('${nomeEsc}','ano','all')">todos</button>
    ${m.anos.map(a => `<button class="chip ${cur.ano === a ? 'active' : ''}" onclick="setStatsFilter('${nomeEsc}','ano',${a})">${a}</button>`).join('')}`;

  const faseBar = document.getElementById('stats-fase-' + slug);
  faseBar.innerHTML = (m.fases && m.fases.length > 1) ? `
    <span class="filter-label">fase</span>
    <button class="chip ${cur.fase === 'all' ? 'active' : ''}" onclick="setStatsFilter('${nomeEsc}','fase','all')">todas</button>
    ${m.fases.map(f => `<button class="chip ${cur.fase === f ? 'active' : ''}" onclick="setStatsFilter('${nomeEsc}','fase',${f})">${f}ª fase</button>`).join('')}` : '';
}

function applyStatsData(m) {
  const slug = statsSlug(m.nome);
  const f = statsState[m.nome];
  const { subs, total, totalTags, multiTagQ } = aggregateStats(m, f);
  const wrap = document.querySelector(`#stats-chart-wrap-${slug}`);
  const metaEl = document.getElementById('stats-meta-' + slug);
  const parts = [];
  parts.push(f.vestibular === 'all' ? 'todos os vestibulares' : f.vestibular);
  parts.push(f.ano === 'all' ? 'todos os anos' : `ano ${f.ano}`);
  parts.push(f.fase === 'all' ? 'todas as fases' : `${f.fase}ª fase`);
  const multiNote = multiTagQ > 0
    ? ` · ${multiTagQ} com múltiplos assuntos (${totalTags} marcações)`
    : '';
  metaEl.textContent = `${total} questões · ${parts.join(' · ')}${multiNote}`;

  if (!subs.length) {
    if (statsCharts[m.nome]) { statsCharts[m.nome].destroy(); delete statsCharts[m.nome]; }
    wrap.innerHTML = '<div class="stats-empty">Nenhuma questão com os filtros aplicados.</div>';
    wrap.style.height = '';
    return;
  }

  wrap.style.height = Math.max(260, subs.length * 22 + 40) + 'px';
  if (!wrap.querySelector('canvas')) wrap.innerHTML = `<canvas id="stats-chart-${slug}"></canvas>`;
  const canvas = wrap.querySelector('canvas');

  const labels = subs.map(s => `${s.id} ${s.nome}`);
  const values = subs.map(s => +s.pct.toFixed(2));

  if (statsCharts[m.nome]) {
    const chart = statsCharts[m.nome];
    chart.data.labels = labels;
    chart.data.datasets[0].data = values;
    chart.$subs = subs;
    chart.$total = total;
    chart.update();
    return;
  }

  const chart = new Chart(canvas, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: '#0F2A5C',
        hoverBackgroundColor: '#1E3A8A',
        borderRadius: 2,
        barThickness: 14,
      }],
    },
    options: {
      indexAxis: 'y',
      maintainAspectRatio: false,
      responsive: true,
      animation: { duration: 250 },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: c => {
              const s = c.chart.$subs[c.dataIndex];
              return `${s.count} questões · aparece em ${s.pct.toFixed(1)}% das ${c.chart.$total}`;
            }
          }
        }
      },
      scales: {
        x: {
          beginAtZero: true,
          ticks: { callback: v => v + '%', font: { size: 11, family: "'Inter', sans-serif" }, color: '#94A3B8' },
          grid: { color: 'rgba(15, 42, 92, 0.06)' }
        },
        y: {
          ticks: { font: { size: 11, family: "'Inter', sans-serif" }, autoSkip: false, color: '#0F172A' },
          grid: { display: false }
        }
      }
    }
  });
  chart.$subs = subs;
  chart.$total = total;
  statsCharts[m.nome] = chart;
}

function buildStatsUI() {
  const wrap = document.getElementById('stats-wrap');
  if (wrap.dataset.built === '1') return;
  DATA.forEach(m => {
    if (!(m.nome in statsState)) statsState[m.nome] = { vestibular: 'all', ano: 'all', fase: 'all' };
  });
  wrap.innerHTML = DATA.map(m => {
    const slug = statsSlug(m.nome);
    return `
      <section class="stats-section">
        <div class="stats-head">
          <h2>${m.nome}</h2>
          <div class="stats-meta" id="stats-meta-${slug}"></div>
        </div>
        <div class="stats-filters">
          <div class="filter-bar" id="stats-vest-${slug}"></div>
          <div class="filter-bar" id="stats-year-${slug}"></div>
          <div class="filter-bar" id="stats-fase-${slug}"></div>
        </div>
        <div class="stats-chart-wrap" id="stats-chart-wrap-${slug}"><canvas id="stats-chart-${slug}"></canvas></div>
      </section>`;
  }).join('');
  DATA.forEach(m => { renderStatsFilters(m); applyStatsData(m); });
  buildHistoricoSection();
  wrap.dataset.built = '1';
}

// ── HISTÓRICO POR ASSUNTO ────────────────────────────────────────────

const historicoState = {
  materia: 'Física',
  subId: '2.1',
};
let historicoChart = null;

function getSubById(m, subId) {
  for (const b of m.blocos) {
    for (const s of b.subareas) if (s.id === subId) return s;
  }
  return null;
}

function buildHistoricoSection() {
  const wrap = document.getElementById('stats-wrap');
  const section = document.createElement('section');
  section.className = 'stats-section';
  section.id = 'historico-section';
  section.innerHTML = `
    <div class="stats-head">
      <h2>Histórico por assunto</h2>
      <div class="stats-meta" id="historico-meta"></div>
    </div>
    <div class="stats-filters">
      <div class="filter-bar" id="historico-materia-bar"></div>
      <div class="filter-bar historico-sub-row">
        <span class="filter-label">assunto</span>
        <select id="historico-sub-select" class="historico-select" onchange="setHistoricoSub(this.value)"></select>
      </div>
    </div>
    <div class="stats-chart-wrap" id="historico-chart-wrap">
      <canvas id="historico-chart"></canvas>
    </div>
  `;
  wrap.appendChild(section);
  renderHistoricoSelectors();
  applyHistoricoChart();
}

function renderHistoricoSelectors() {
  const bar = document.getElementById('historico-materia-bar');
  bar.innerHTML = `<span class="filter-label">matéria</span>` + DATA.map(m => {
    const esc = m.nome.replace(/'/g, "\\'");
    const active = historicoState.materia === m.nome ? ' active' : '';
    return `<button class="chip${active}" onclick="setHistoricoMateria('${esc}')">${m.nome}</button>`;
  }).join('');

  const m = getM(historicoState.materia);
  const sel = document.getElementById('historico-sub-select');
  const curSub = getSubById(m, historicoState.subId);
  if (!curSub) historicoState.subId = m.blocos[0]?.subareas[0]?.id || '';
  sel.innerHTML = m.blocos.map(b =>
    `<optgroup label="${b.id} · ${b.nome}">` +
    b.subareas.map(s => `<option value="${s.id}"${s.id === historicoState.subId ? ' selected' : ''}>${s.id} ${s.nome}</option>`).join('') +
    `</optgroup>`
  ).join('');
}

function applyHistoricoChart() {
  const m = getM(historicoState.materia);
  const sub = getSubById(m, historicoState.subId);
  if (!sub) return;
  const anos = m.anos;
  const ita = anos.map(a => sub.questoes.filter(q => q.ano === a && (q.vestibular || 'ITA') === 'ITA').length);
  const ime = anos.map(a => sub.questoes.filter(q => q.ano === a && q.vestibular === 'IME').length);
  const ambos = anos.map((_, i) => ita[i] + ime[i]);

  const totalITA = ita.reduce((s, n) => s + n, 0);
  const totalIME = ime.reduce((s, n) => s + n, 0);
  document.getElementById('historico-meta').textContent =
    `${sub.id} · ${sub.nome} · ${totalITA + totalIME} questões (ITA ${totalITA} · IME ${totalIME})`;

  const canvas = document.getElementById('historico-chart');
  if (historicoChart) {
    historicoChart.data.labels = anos;
    historicoChart.data.datasets[0].data = ita;
    historicoChart.data.datasets[1].data = ime;
    historicoChart.data.datasets[2].data = ambos;
    historicoChart.update();
    return;
  }
  historicoChart = new Chart(canvas, {
    type: 'line',
    data: {
      labels: anos,
      datasets: [
        { label: 'ITA', data: ita, borderColor: '#0F2A5C', backgroundColor: 'rgba(15,42,92,0.08)', tension: 0.35, fill: false, borderWidth: 2, pointRadius: 3.5, pointHoverRadius: 6, pointBackgroundColor: '#0F2A5C' },
        { label: 'IME', data: ime, borderColor: '#1E3A8A', backgroundColor: 'rgba(30,58,138,0.08)', tension: 0.35, fill: false, borderWidth: 2, pointRadius: 3.5, pointHoverRadius: 6, pointBackgroundColor: '#1E3A8A' },
        { label: 'ITA + IME', data: ambos, borderColor: '#94A3B8', backgroundColor: 'rgba(148,163,184,0.08)', tension: 0.35, fill: false, borderWidth: 1.5, pointRadius: 3, pointHoverRadius: 5, pointBackgroundColor: '#94A3B8', borderDash: [6, 4] },
      ],
    },
    options: {
      maintainAspectRatio: false,
      responsive: true,
      animation: { duration: 280 },
      plugins: {
        legend: { position: 'top', align: 'end', labels: { boxWidth: 18, boxHeight: 2, font: { size: 12, family: "'Inter', sans-serif" }, color: '#475569', padding: 14 } },
        tooltip: { mode: 'index', intersect: false },
      },
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 11, family: "'Inter', sans-serif" }, color: '#94A3B8' } },
        y: { beginAtZero: true, ticks: { precision: 0, font: { size: 11, family: "'Inter', sans-serif" }, color: '#94A3B8' }, grid: { color: 'rgba(15, 42, 92, 0.06)' } },
      },
    },
  });
}

function setHistoricoMateria(nome) {
  historicoState.materia = nome;
  const m = getM(nome);
  historicoState.subId = m.blocos[0]?.subareas[0]?.id || '';
  renderHistoricoSelectors();
  applyHistoricoChart();
}
function setHistoricoSub(id) {
  historicoState.subId = id;
  applyHistoricoChart();
}

function setStatsFilter(materiaNome, key, value) {
  const cur = statsState[materiaNome];
  cur[key] = value;
  const m = getM(materiaNome);
  renderStatsFilters(m);
  applyStatsData(m);
}

// ── INIT ──────────────────────────────────────────────────────────────

const total = DATA.reduce((s, m) => s + m.total, 0);
document.getElementById('sb-total').textContent = total;

renderMateriaList();
renderYearFilter();
renderFaseFilter();
renderContent();

// ── AUTO-HIDE TOP NAV ─────────────────────────────────────────────────
(function setupAutoHideNav() {
  const nav = document.getElementById('top-tabs');
  const corner = document.querySelector('.ita-logo-corner');
  if (!nav) return;
  const SHOW_AT = 80;
  const HIDE_DELTA = 10;
  let lastY = window.scrollY;
  let hideAnchor = lastY;
  let ticking = false;

  function show() {
    nav.classList.remove('nav-hidden');
    if (corner) corner.classList.remove('nav-hidden');
  }
  function hide() {
    nav.classList.add('nav-hidden');
    if (corner) corner.classList.add('nav-hidden');
  }

  function onScroll() {
    const y = Math.max(0, window.scrollY);
    if (y < SHOW_AT) {
      show();
      hideAnchor = y;
    } else if (y < lastY) {
      show();
      hideAnchor = y;
    } else if (y > hideAnchor + HIDE_DELTA) {
      hide();
      hideAnchor = y;
    }
    lastY = y;
    ticking = false;
  }
  window.addEventListener('scroll', () => {
    if (!ticking) { requestAnimationFrame(onScroll); ticking = true; }
  }, { passive: true });
})();
