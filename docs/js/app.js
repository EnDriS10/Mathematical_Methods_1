/* Página: pestañas de hojas, índice de ejercicios, resolución (KaTeX) y gráficas interactivas. */
(function () {
  'use strict';
  const $ = (s, r) => (r || document).querySelector(s);
  const el = (tag, attrs, ...kids) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) { if (k === 'class') n.className = v; else if (k === 'html') n.innerHTML = v; else if (k.startsWith('on')) n.addEventListener(k.slice(2), v); else if (v != null && v !== false) n.setAttribute(k, v === true ? '' : v); }
    for (const kid of kids) n.append(kid);
    return n;
  };
  const MATH = { delimiters: [{ left: '\\[', right: '\\]', display: true }, { left: '\\(', right: '\\)', display: false }], throwOnError: false, strict: 'ignore' };
  const renderMath = (node) => window.renderMathInElement && window.renderMathInElement(node, MATH);

  let sheets = [], catalog = {}, current = null, observer = null;

  async function init() {
    const [s, c] = await Promise.all([fetch('data/sheets.json').then((r) => r.json()), fetch('data/catalog.json').then((r) => r.json())]);
    sheets = s.sheets; catalog = c;
    $('#autor').textContent = s.site.name; $('#asignatura').textContent = s.site.course;
    document.title = s.site.name + ' · ' + s.site.course;
    buildTabs();
    window.addEventListener('hashchange', route);
    route();
    const btn = $('#tema');
    const label = () => { btn.textContent = effectiveTheme() === 'dark' ? 'Tema claro' : 'Tema oscuro'; };
    btn.addEventListener('click', () => { const t = effectiveTheme() === 'dark' ? 'light' : 'dark'; document.documentElement.dataset.theme = t; try { localStorage.setItem('tema', t); } catch (e) {} label(); });
    label();
  }
  const effectiveTheme = () => document.documentElement.dataset.theme || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');

  function buildTabs() {
    const nav = $('#tabs');
    nav.replaceChildren(...sheets.map((sh) => {
      const empty = !sh.problems.length;
      const a = el('a', { href: '#hoja-' + sh.n, class: 'tab' + (empty ? ' soon' : ''), 'data-n': sh.n }, sh.title, empty ? el('small', {}, 'próximamente') : '');
      return a;
    }));
  }

  function route() {
    const m = /^#hoja-(\d+)(?:\/(\d+))?/.exec(location.hash);
    const n = m ? +m[1] : (sheets.find((s) => s.problems.length) || sheets[0]).n;
    const sheet = sheets.find((s) => s.n === n) || sheets[0];
    if (current !== sheet.n) { show(sheet); current = sheet.n; }
    if (m && m[2]) {
      const go = () => { const t = document.getElementById('p-' + sheet.n + '-' + m[2]); if (t) t.scrollIntoView({ block: 'start' }); };
      go(); setTimeout(go, 350); setTimeout(go, 1000);   // los gráficos se crean al aparecer; reajusta tras el primer dibujo
    }
    document.querySelectorAll('.tab').forEach((t) => t.setAttribute('aria-current', +t.dataset.n === sheet.n ? 'page' : 'false'));
  }

  function show(sheet) {
    if (observer) observer.disconnect();
    const main = $('#hoja'), idx = $('#indice');
    main.replaceChildren();
    if (!sheet.problems.length) {
      main.append(el('section', { class: 'empty' }, el('h2', {}, sheet.title), el('p', {}, 'Esta hoja aún no tiene ejercicios resueltos. Cuando añadas sus soluciones al LaTeX y ejecutes el script de construcción, aparecerán aquí.')));
      idx.replaceChildren();
      return;
    }
    idx.replaceChildren(el('p', { class: 'idx-title' }, sheet.title), el('ol', {}, ...sheet.problems.map((p) =>
      el('li', {}, el('a', { href: '#hoja-' + sheet.n + '/' + p.num, 'aria-label': 'Ejercicio ' + p.num }, String(p.num))))));
    const lazy = [];
    for (const p of sheet.problems) {
      const spec = catalog[p.id];
      const card = el('article', { class: 'problem', id: 'p-' + sheet.n + '-' + p.num },
        el('header', { class: 'phead' }, el('span', { class: 'num' }, String(p.num)), el('div', { class: 'statement', html: p.statement })));
      const body = el('div', { class: 'pbody' });
      const sol = el('details', { class: 'solution', open: true }, el('summary', {}, 'Resolución'), el('div', { class: 'sol-text', html: p.solution }));
      body.append(sol);
      if (spec) {
        const panel = el('section', { class: 'panel', 'aria-label': 'Gráfica interactiva del ejercicio ' + p.num },
          el('p', { class: 'caption', html: '\\(' + spec.tex + '\\)' }));
        const host = el('div', { class: 'host' });
        panel.append(host); body.append(panel);
        lazy.push([host, spec]);
      }
      card.append(body); main.append(card);
    }
    renderMath(main);
    observer = new IntersectionObserver((entries) => {
      for (const e of entries) if (e.isIntersecting) {
        const item = lazy.find((l) => l[0] === e.target); if (!item || item[0].dataset.ready) continue;
        item[0].dataset.ready = '1';
        try { item[0].__plot = new window.EdoPlot(item[0], item[1]); } catch (err) { item[0].textContent = 'No se pudo dibujar esta gráfica.'; console.error(item[1].id, err); }
        observer.unobserve(e.target);
      }
    }, { rootMargin: '400px 0px' });
    for (const [host] of lazy) observer.observe(host);
    window.scrollTo(0, 0);
  }

  init().catch((e) => { $('#hoja').textContent = 'No se pudieron cargar los datos: ' + e.message; console.error(e); });
})();
