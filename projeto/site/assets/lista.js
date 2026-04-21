// ── CRIAR LISTA ───────────────────────────────────────────────────────
// Depende de window.DATA exposto por banco.js

const listaState = {
  selected: [],      // array de ids (ordem importa)
  materia: null,     // nome da matéria (null = todas)
  vestibular: 'all',
  ano: 'all',
  fase: 'all',
  bloco: 'all',      // id do bloco (ou 'all')
  sub: 'all',        // id da subárea (ou 'all')
  busca: '',
  titulo: 'Lista de questões',
  subtitulo: '',
  incluirGabarito: true,
  incluirAlternativas: true,
  incluirObs: false,
  built: false,
};

const listaIndex = {};  // id → {q, materia}

function buildListaIndex() {
  const DATA = window.DATA;
  for (const m of DATA) {
    for (const bloco of m.blocos) {
      for (const sub of bloco.subareas) {
        for (const q of sub.questoes) {
          if (!listaIndex[q.id]) listaIndex[q.id] = { q, materia: m };
        }
      }
    }
  }
}

function buildListaUI() {
  if (listaState.built) {
    renderLista();
    return;
  }
  buildListaIndex();
  const wrap = document.getElementById('lista-wrap');
  wrap.innerHTML = `
    <div class="lista-head">
      <div class="lista-title-row">
        <h1>Criar lista de questões</h1>
        <div class="lista-actions">
          <button class="lista-btn ghost" onclick="clearLista()">limpar</button>
          <button class="lista-btn" onclick="exportListaPDF()">exportar PDF</button>
          <button class="lista-btn primary" onclick="exportListaDOCX()">exportar DOCX</button>
        </div>
      </div>
      <div class="lista-meta-form">
        <input type="text" id="lista-titulo" placeholder="Título da lista" value="${listaState.titulo}" oninput="updateListaField('titulo', this.value)">
        <input type="text" id="lista-subtitulo" placeholder="Subtítulo (opcional)" value="${listaState.subtitulo}" oninput="updateListaField('subtitulo', this.value)">
      </div>
      <div class="lista-opts">
        <label><input type="checkbox" ${listaState.incluirGabarito ? 'checked' : ''} onchange="updateListaField('incluirGabarito', this.checked)"> gabarito ao final</label>
        <label><input type="checkbox" ${listaState.incluirAlternativas ? 'checked' : ''} onchange="updateListaField('incluirAlternativas', this.checked)"> incluir alternativas</label>
        <label><input type="checkbox" ${listaState.incluirObs ? 'checked' : ''} onchange="updateListaField('incluirObs', this.checked)"> incluir observações</label>
      </div>
    </div>

    <div class="lista-body">
      <div class="lista-available">
        <div class="lista-filters" id="lista-filters"></div>
        <div class="lista-search-row">
          <input type="text" id="lista-busca" placeholder="buscar por texto, ano, tópico…" oninput="updateBusca(this.value)">
          <span class="lista-count" id="lista-avail-count"></span>
          <button class="lista-bulk-btn" id="lista-bulk-btn" onclick="toggleAllFiltered()"></button>
        </div>
        <div class="lista-questoes" id="lista-questoes"></div>
      </div>

      <div class="lista-selected">
        <div class="lista-sel-head">
          <h2>Lista atual</h2>
          <span class="lista-sel-count" id="lista-sel-count">0 questões</span>
        </div>
        <div class="lista-sel-body" id="lista-sel-body"></div>
      </div>
    </div>
  `;
  listaState.built = true;
  renderLista();
}

function updateListaField(k, v) {
  listaState[k] = v;
}

function updateBusca(v) {
  listaState.busca = v.trim().toLowerCase();
  renderAvailable();
}

function renderLista() {
  renderFilters();
  renderAvailable();
  renderSelected();
}

function renderFilters() {
  const DATA = window.DATA;
  const m = listaState.materia ? DATA.find(x => x.nome === listaState.materia) : null;
  const anos = m ? m.anos : [...new Set(DATA.flatMap(d => d.anos))].sort();
  const fases = m ? (m.fases || []) : [...new Set(DATA.flatMap(d => d.fases || []))].sort();

  const materiaBtns = [
    `<button class="chip ${!listaState.materia ? 'active' : ''}" onclick="setListaMateria(null)">todas</button>`,
    ...DATA.map(d => `<button class="chip ${listaState.materia === d.nome ? 'active' : ''}" onclick="setListaMateria('${d.nome.replace(/'/g, "\\'")}')">${d.nome}</button>`),
  ].join('');

  const vestBtns = `
    <button class="chip ${listaState.vestibular === 'all' ? 'active' : ''}" onclick="setListaFilter('vestibular','all')">todos</button>
    <button class="chip ${listaState.vestibular === 'ITA' ? 'active' : ''}" onclick="setListaFilter('vestibular','ITA')">ITA</button>
    <button class="chip ${listaState.vestibular === 'IME' ? 'active' : ''}" onclick="setListaFilter('vestibular','IME')">IME</button>
  `;

  const anoBtns = `
    <button class="chip ${listaState.ano === 'all' ? 'active' : ''}" onclick="setListaFilter('ano','all')">todos</button>
    ${anos.map(a => `<button class="chip ${listaState.ano === a ? 'active' : ''}" onclick="setListaFilter('ano',${a})">${a}</button>`).join('')}
  `;

  const faseBtns = fases.length > 1 ? `
    <div class="lista-filter-row">
      <span class="filter-label">fase</span>
      <button class="chip ${listaState.fase === 'all' ? 'active' : ''}" onclick="setListaFilter('fase','all')">todas</button>
      ${fases.map(f => `<button class="chip ${listaState.fase === f ? 'active' : ''}" onclick="setListaFilter('fase',${f})">${f}ª</button>`).join('')}
    </div>` : '';

  let blocoBtns = '';
  let subBtns = '';
  if (m) {
    blocoBtns = `
      <div class="lista-filter-row">
        <span class="filter-label">bloco</span>
        <button class="chip ${listaState.bloco === 'all' ? 'active' : ''}" onclick="setListaFilter('bloco','all')">todos</button>
        ${m.blocos.map(b => `<button class="chip ${listaState.bloco === b.id ? 'active' : ''}" onclick="setListaFilter('bloco','${b.id}')">${b.id} ${b.nome}</button>`).join('')}
      </div>`;
    if (listaState.bloco !== 'all') {
      const bloco = m.blocos.find(b => b.id === listaState.bloco);
      if (bloco) {
        subBtns = `
          <div class="lista-filter-row">
            <span class="filter-label">subárea</span>
            <button class="chip ${listaState.sub === 'all' ? 'active' : ''}" onclick="setListaFilter('sub','all')">todas</button>
            ${bloco.subareas.map(s => `<button class="chip ${listaState.sub === s.id ? 'active' : ''}" onclick="setListaFilter('sub','${s.id}')">${s.id} ${s.nome}</button>`).join('')}
          </div>`;
      }
    }
  }

  document.getElementById('lista-filters').innerHTML = `
    <div class="lista-filter-row"><span class="filter-label">matéria</span>${materiaBtns}</div>
    <div class="lista-filter-row"><span class="filter-label">vestibular</span>${vestBtns}</div>
    <div class="lista-filter-row"><span class="filter-label">ano</span>${anoBtns}</div>
    ${faseBtns}
    ${blocoBtns}
    ${subBtns}
  `;
}

function setListaMateria(nome) {
  listaState.materia = nome;
  listaState.bloco = 'all';
  listaState.sub = 'all';
  // reset ano/fase if não existir mais
  if (nome) {
    const m = window.DATA.find(d => d.nome === nome);
    if (listaState.ano !== 'all' && !m.anos.includes(listaState.ano)) listaState.ano = 'all';
    if (listaState.fase !== 'all' && !(m.fases || []).includes(listaState.fase)) listaState.fase = 'all';
  }
  renderLista();
}

function setListaFilter(k, v) {
  listaState[k] = v;
  if (k === 'bloco') listaState.sub = 'all';
  renderLista();
}

function questoesFiltradas() {
  const DATA = window.DATA;
  const materias = listaState.materia ? [DATA.find(d => d.nome === listaState.materia)].filter(Boolean) : DATA;
  const out = [];
  const seen = new Set();
  for (const m of materias) {
    for (const bloco of m.blocos) {
      if (listaState.bloco !== 'all' && bloco.id !== listaState.bloco && listaState.materia) continue;
      for (const sub of bloco.subareas) {
        if (listaState.sub !== 'all' && sub.id !== listaState.sub && listaState.materia) continue;
        for (const q of sub.questoes) {
          if (seen.has(q.id)) continue;
          if (listaState.vestibular !== 'all' && (q.vestibular || 'ITA') !== listaState.vestibular) continue;
          if (listaState.ano !== 'all' && q.ano !== listaState.ano) continue;
          if (listaState.fase !== 'all' && (q.fase || 1) !== listaState.fase) continue;
          if (listaState.busca) {
            const hay = ((q.enunciado_md || '') + ' ' + (q.topicos_ids || []).join(' ') + ' ' + q.ano + ' ' + (q.vestibular || '')).toLowerCase();
            if (!hay.includes(listaState.busca)) continue;
          }
          seen.add(q.id);
          out.push({ q, materia: m, sub, bloco });
        }
      }
    }
  }
  out.sort((a, b) => {
    if (a.materia.nome !== b.materia.nome) return a.materia.nome.localeCompare(b.materia.nome);
    if (a.q.ano !== b.q.ano) return b.q.ano - a.q.ano;
    if ((a.q.vestibular || '') !== (b.q.vestibular || '')) return (a.q.vestibular || '').localeCompare(b.q.vestibular || '');
    return a.q.numero - b.q.numero;
  });
  return out;
}

function renderAvailable() {
  const list = questoesFiltradas();
  document.getElementById('lista-avail-count').textContent = `${list.length} questões`;
  const selSet = new Set(listaState.selected);
  renderBulkBtn(list, selSet);
  const cont = document.getElementById('lista-questoes');
  if (!list.length) {
    cont.innerHTML = '<div class="lista-empty">Nenhuma questão encontrada com os filtros atuais.</div>';
    return;
  }
  cont.innerHTML = list.slice(0, 200).map(({ q, materia, sub }) => {
    const vest = q.vestibular || 'ITA';
    const vestCls = vest.toLowerCase();
    const isSel = selSet.has(q.id);
    const preview = q.usa_imagem && q.img_src
      ? `<img src="${q.img_src}" alt="" loading="lazy">`
      : escHtml((q.enunciado_md || '').slice(0, 220)) + ((q.enunciado_md || '').length > 220 ? '…' : '');
    return `
      <div class="lista-card ${vestCls} ${isSel ? 'selected' : ''}">
        <div class="lista-card-head">
          <span class="q-inst ${vestCls}">${vest}</span>
          <span class="q-year">${q.ano}</span>
          <span class="q-num">Q${q.numero}${q.fase ? ` · ${q.fase}ª fase` : ''}</span>
          <span class="lista-card-materia">${materia.nome}</span>
          <span class="lista-card-tag">${sub.id}</span>
          <span class="rule"></span>
          ${isSel
            ? `<button class="lista-add-btn added" onclick="toggleListaQ('${q.id}')">✓ adicionada</button>`
            : `<button class="lista-add-btn" onclick="toggleListaQ('${q.id}')">+ adicionar</button>`}
        </div>
        <div class="lista-card-preview">${preview}</div>
      </div>`;
  }).join('') + (list.length > 200 ? `<div class="lista-more">Mostrando 200 de ${list.length}. Refine os filtros para ver mais.</div>` : '');
}

function renderBulkBtn(list, selSet) {
  const btn = document.getElementById('lista-bulk-btn');
  if (!btn) return;
  if (!list.length) {
    btn.textContent = '';
    btn.style.display = 'none';
    return;
  }
  btn.style.display = '';
  const ids = list.map(x => x.q.id);
  const missing = ids.filter(id => !selSet.has(id));
  if (missing.length === 0) {
    btn.textContent = `✕ remover todas (${ids.length})`;
    btn.classList.add('all-added');
  } else {
    btn.textContent = `+ adicionar todas (${missing.length})`;
    btn.classList.remove('all-added');
  }
}

function toggleAllFiltered() {
  const list = questoesFiltradas();
  if (!list.length) return;
  const ids = list.map(x => x.q.id);
  const selSet = new Set(listaState.selected);
  const missing = ids.filter(id => !selSet.has(id));
  if (missing.length > 0) {
    listaState.selected.push(...missing);
  } else {
    const removeSet = new Set(ids);
    listaState.selected = listaState.selected.filter(id => !removeSet.has(id));
  }
  renderAvailable();
  renderSelected();
}

function toggleListaQ(id) {
  const idx = listaState.selected.indexOf(id);
  if (idx >= 0) listaState.selected.splice(idx, 1);
  else listaState.selected.push(id);
  renderAvailable();
  renderSelected();
}

function moveListaQ(id, dir) {
  const idx = listaState.selected.indexOf(id);
  if (idx < 0) return;
  const ni = idx + dir;
  if (ni < 0 || ni >= listaState.selected.length) return;
  [listaState.selected[idx], listaState.selected[ni]] = [listaState.selected[ni], listaState.selected[idx]];
  renderSelected();
}

function removeListaQ(id) {
  const idx = listaState.selected.indexOf(id);
  if (idx < 0) return;
  listaState.selected.splice(idx, 1);
  renderAvailable();
  renderSelected();
}

function clearLista() {
  if (!listaState.selected.length) return;
  if (!confirm('Limpar toda a lista?')) return;
  listaState.selected = [];
  renderAvailable();
  renderSelected();
}

function renderSelected() {
  const body = document.getElementById('lista-sel-body');
  document.getElementById('lista-sel-count').textContent = `${listaState.selected.length} questões`;
  if (!listaState.selected.length) {
    body.innerHTML = '<div class="lista-empty">Nenhuma questão selecionada ainda. Use o painel à esquerda para adicionar.</div>';
    return;
  }
  body.innerHTML = listaState.selected.map((id, i) => {
    const entry = listaIndex[id];
    if (!entry) return '';
    const { q, materia } = entry;
    const vest = q.vestibular || 'ITA';
    const vestCls = vest.toLowerCase();
    return `
      <div class="lista-sel-item ${vestCls}">
        <span class="lista-sel-num">${i + 1}</span>
        <div class="lista-sel-info">
          <div class="lista-sel-meta">
            <span class="q-inst ${vestCls}">${vest}</span>
            <span>${q.ano}${q.fase ? ` · ${q.fase}ª fase` : ''}</span>
            <span>Q${q.numero}</span>
            <span class="lista-sel-mat">${materia.nome}</span>
          </div>
          <div class="lista-sel-preview">${q.usa_imagem ? '[imagem]' : escHtml((q.enunciado_md || '').slice(0, 120)) + '…'}</div>
        </div>
        <div class="lista-sel-controls">
          <button title="subir" onclick="moveListaQ('${q.id}', -1)" ${i === 0 ? 'disabled' : ''}>▲</button>
          <button title="descer" onclick="moveListaQ('${q.id}', 1)" ${i === listaState.selected.length - 1 ? 'disabled' : ''}>▼</button>
          <button title="remover" class="rm" onclick="removeListaQ('${q.id}')">✕</button>
        </div>
      </div>`;
  }).join('');
}

function escHtml(s) {
  return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// ── EXPORT ────────────────────────────────────────────────────────────

function buildListaExportHTML(opts = {}) {
  const { forPrint = false } = opts;
  if (!listaState.selected.length) return null;

  const items = listaState.selected.map((id, i) => {
    const entry = listaIndex[id];
    if (!entry) return '';
    const { q, materia } = entry;
    const vest = q.vestibular || 'ITA';
    const header = `${vest} · ${q.ano}${q.fase ? ` · ${q.fase}ª fase` : ''} · ${materia.nome} · Q${q.numero}`;
    let body = '';
    if (q.usa_imagem && q.img_src) {
      body = `<p class="q-img-wrap"><img src="${q.img_src}" alt="Questão ${q.numero}"></p>`;
    } else {
      body = `<div class="q-text">${escHtml(q.enunciado_md || '')}</div>`;
      if (listaState.incluirAlternativas && q.alternativas) {
        const alts = Object.entries(q.alternativas).map(([k, v]) =>
          `<div class="q-alt"><b>${k})</b> ${escHtml(v)}</div>`).join('');
        body += `<div class="q-alts">${alts}</div>`;
      }
    }
    let obs = '';
    if (listaState.incluirObs && q.obs) {
      obs = `<div class="q-obs"><i>${escHtml(q.obs)}</i></div>`;
    }
    return `
      <section class="q-item">
        <div class="q-header"><b>${i + 1}.</b> <span>${header}</span></div>
        ${body}
        ${obs}
      </section>`;
  }).join('');

  let gabaritos = '';
  if (listaState.incluirGabarito) {
    const rows = listaState.selected.map((id, i) => {
      const entry = listaIndex[id];
      if (!entry) return '';
      return `<span>${i + 1}) ${entry.q.gabarito || '—'}</span>`;
    }).join('');
    gabaritos = `
      <section class="q-gab-section">
        <h2>Gabarito</h2>
        <div class="q-gab-grid">${rows}</div>
      </section>`;
  }

  const sub = listaState.subtitulo ? `<div class="lista-subtitle">${escHtml(listaState.subtitulo)}</div>` : '';
  const styles = `
    body { font-family: Georgia, 'Times New Roman', serif; color: #1a1a1a; line-height: 1.55; max-width: 780px; margin: 0 auto; padding: 28px 36px; background: #fff; }
    h1 { font-size: 22px; color: #0F2A5C; margin-bottom: 4px; font-weight: 600; }
    h2 { font-size: 15px; color: #0F2A5C; margin: 18px 0 8px; font-weight: 600; border-bottom: 1px solid #ccc; padding-bottom: 4px; }
    .lista-subtitle { font-size: 12px; color: #555; margin-bottom: 18px; }
    .q-item { margin-bottom: 20px; padding-bottom: 10px; border-bottom: 0.5px dashed #ddd; page-break-inside: avoid; }
    .q-item:last-of-type { border-bottom: none; }
    .q-header { font-size: 11px; color: #0F2A5C; margin-bottom: 8px; letter-spacing: 0.02em; }
    .q-header b { color: #000; margin-right: 4px; }
    .q-text { white-space: pre-wrap; font-size: 12px; }
    .q-alts { margin-top: 8px; font-size: 12px; }
    .q-alt { margin: 3px 0; }
    .q-img-wrap { margin: 6px 0; }
    .q-img-wrap img { max-width: 100%; height: auto; }
    .q-obs { margin-top: 6px; font-size: 11px; color: #666; }
    .q-gab-section { margin-top: 24px; }
    .q-gab-grid { display: flex; flex-wrap: wrap; gap: 10px 22px; font-size: 12px; font-family: 'Courier New', monospace; }
    ${forPrint ? '@page { size: A4; margin: 18mm; } body { padding: 0; max-width: none; }' : ''}
  `;

  return `<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>${escHtml(listaState.titulo)}</title>
<style>${styles}</style>
</head>
<body>
<h1>${escHtml(listaState.titulo)}</h1>
${sub}
${items}
${gabaritos}
</body>
</html>`;
}

function exportListaPDF() {
  const html = buildListaExportHTML({ forPrint: true });
  if (!html) { alert('Adicione pelo menos uma questão à lista.'); return; }
  const w = window.open('', '_blank');
  if (!w) { alert('O navegador bloqueou a janela de impressão. Permita pop-ups para este site.'); return; }
  w.document.open();
  w.document.write(html);
  w.document.close();
  const doPrint = () => { try { w.focus(); w.print(); } catch (e) {} };
  // aguarda imagens carregarem antes de imprimir
  const imgs = w.document.images;
  if (!imgs.length) { setTimeout(doPrint, 300); return; }
  let loaded = 0;
  const done = () => { if (++loaded >= imgs.length) setTimeout(doPrint, 150); };
  for (const img of imgs) {
    if (img.complete) done();
    else { img.addEventListener('load', done); img.addEventListener('error', done); }
  }
  // timeout de segurança
  setTimeout(doPrint, 6000);
}

function exportListaDOCX() {
  const html = buildListaExportHTML({ forPrint: false });
  if (!html) { alert('Adicione pelo menos uma questão à lista.'); return; }
  if (typeof htmlDocx === 'undefined' || !htmlDocx.asBlob) {
    alert('Biblioteca de exportação DOCX não carregou. Verifique a conexão e recarregue a página.');
    return;
  }
  const blob = htmlDocx.asBlob(html);
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = slugifyLista(listaState.titulo) + '.docx';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function slugifyLista(s) {
  return (s || 'lista').toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'lista';
}
