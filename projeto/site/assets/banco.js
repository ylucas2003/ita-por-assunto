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
        <span class="sb-disc-name">${m.nome}</span>
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

function renderQuestion(q, m) {
  const vest = q.vestibular || 'ITA';
  const vestCls = vest.toLowerCase();
  let stmtHtml;
  if (q.usa_imagem && q.img_src) {
    stmtHtml = `<img src="${q.img_src}" alt="Q${q.numero}" loading="lazy">`;
  } else {
    const enc = (q.enunciado_md || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    stmtHtml = enc;
  }
  const ids = q.topicos_ids || [];
  const materiaEsc = m.nome.replace(/'/g, "\\'");
  const tags = ids.length ? ids.map((tid, i) => {
    const nome = (m.topic_names && m.topic_names[tid]) || '';
    const cls = i === 0 ? 'q-topic-tag primary' : 'q-topic-tag';
    const label = nome ? `${tid} · ${nome}` : tid;
    return `<span class="${cls}" title="${nome}" onclick="setFilter('sub:${tid}','${materiaEsc}')">${label}</span>`;
  }).join('') : '';
  const resBtn = q.resolucao_url
    ? `<a class="q-action-btn" href="${q.resolucao_url}" target="_blank" rel="noopener">resolução ↗</a>`
    : '<span class="q-action-btn disabled">sem resolução</span>';
  const gabBtn = q.gabarito
    ? `<button class="q-gab-btn ${vestCls}" onclick="toggleGabarito(this)" data-gab="${q.gabarito}" type="button">
        <span class="gab-label">gabarito</span>
        <span class="gab-letter">${q.gabarito}</span>
      </button>`
    : '<span class="q-gab-btn disabled">—</span>';
  const caption = q.obs
    ? `<div class="question-caption">${q.obs.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}</div>`
    : '';
  return `
    <article class="question ${vestCls}" data-vest="${vest}" data-ano="${q.ano}">
      <div class="question-main">
        <div class="question-head">
          <span class="q-inst ${vestCls}">${vest}</span>
          <span class="q-year">${q.ano}</span>
          <span class="q-num">Questão ${q.numero}</span>
        </div>
        <div class="question-statement">${stmtHtml}</div>
        ${caption}
      </div>
      <aside class="question-side">
        ${gabBtn}
        ${resBtn}
        ${tags ? `<div class="q-side-tags">${tags}</div>` : ''}
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
    const q = document.querySelector('#tab-mensagem .msg-quote');
    if (q) {
      q.classList.remove('animate-in');
      // força reflow para reiniciar a transição mesmo se já estava visível
      void q.offsetWidth;
      requestAnimationFrame(() => q.classList.add('animate-in'));
    }
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

  // Total de questões únicas que casam com o filtro (base para %)
  const matched = new Set();
  for (const bloco of m.blocos) {
    for (const sub of bloco.subareas) {
      for (const q of sub.questoes) {
        if (match(q)) matched.add(q.id);
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
  return { subs, total };
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
  const { subs, total } = aggregateStats(m, f);
  const wrap = document.querySelector(`#stats-chart-wrap-${slug}`);
  const metaEl = document.getElementById('stats-meta-' + slug);
  const parts = [];
  parts.push(f.vestibular === 'all' ? 'todos os vestibulares' : f.vestibular);
  parts.push(f.ano === 'all' ? 'todos os anos' : `ano ${f.ano}`);
  parts.push(f.fase === 'all' ? 'todas as fases' : `${f.fase}ª fase`);
  metaEl.textContent = `${total} questões · ${parts.join(' · ')}`;

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
        backgroundColor: '#14148a',
        hoverBackgroundColor: '#2424b3',
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
              return `${s.count} questões · ${s.pct.toFixed(1)}% das ${c.chart.$total} totais`;
            }
          }
        }
      },
      scales: {
        x: {
          beginAtZero: true,
          ticks: { callback: v => v + '%', font: { size: 11 }, color: '#888780' },
          grid: { color: 'rgba(0,0,0,0.05)' }
        },
        y: {
          ticks: { font: { size: 11 }, autoSkip: false, color: '#2c2c2a' },
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
  wrap.dataset.built = '1';
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
