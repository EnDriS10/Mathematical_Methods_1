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

  let sheets = [], catalog = {}, site = {}, current = null, observer = null;

  async function init() {
    const [s, c] = await Promise.all([fetch('data/sheets.json').then((r) => r.json()), fetch('data/catalog.json').then((r) => r.json())]);
    sheets = s.sheets; catalog = c; site = s.site;
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
    nav.replaceChildren(el('a', { href: '#inicio', class: 'tab', 'data-n': 'inicio' }, 'Inicio'), ...sheets.map((sh) =>
      el('a', { href: '#hoja-' + sh.n, class: 'tab' + (sh.problems.length ? '' : ' soon'), 'data-n': sh.n }, sh.title)));
  }

  function route() {
    const m = /^#hoja-(\d+)(?:\/(\d+))?/.exec(location.hash);
    const sheet = m ? sheets.find((s) => s.n === +m[1]) : null;
    const key = sheet ? sheet.n : 'inicio';
    if (current !== key) { if (sheet) show(sheet); else home(); current = key; }
    if (sheet && m[2]) {
      const go = () => { const t = document.getElementById('p-' + sheet.n + '-' + m[2]); if (t) t.scrollIntoView({ block: 'start' }); };
      go(); setTimeout(go, 350); setTimeout(go, 1000);   // los gráficos se crean al aparecer; reajusta tras el primer dibujo
    }
    document.querySelectorAll('.tab').forEach((t) => t.setAttribute('aria-current', String(t.dataset.n) === String(key) ? 'page' : 'false'));
  }

  /* ---------- gráficos decorativos del inicio (misma ecuación y motor que la web) ---------- */
  const E = () => window.EdoEngine;
  const cssVar = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  function familyOf(spec, n) {
    const eng = E(), cn = spec.consts.map((c) => c.name), base = spec.consts.map((c) => c.value);
    const idx = spec.consts.findIndex((c) => c.sweep !== false && !c.integer && c.role !== 'level');
    const c = spec.consts[idx], w = spec.window, view = { x0: w[0], x1: w[1], y0: w[2], y1: w[3] };
    const fns = (Array.isArray(spec.y) ? spec.y : [spec.y]).map((t) => eng.compile(String(t), ['x'], cn, spec.defs || []));
    const valid = spec.valid ? eng.compile(String(spec.valid), ['x'], cn, spec.defs || []) : null;
    const X0 = Float64Array.from({ length: 900 }, (_, i) => w[0] + (w[1] - w[0]) * i / 899);
    const make = (v) => { const K = base.slice(); K[idx] = v; const out = [];
      for (const f of fns) { const r = eng.sampleExplicit(f, valid, K, X0); out.push(...eng.splitCurve(r.X, r.Y, view)); } return out; };
    return { view, family: eng.sweepValues(Object.assign({}, c, { n })).map(make), sel: make(c.value) };
  }
  function paint(canvas, fam, opts) {
    opts = opts || {};
    const dpr = window.devicePixelRatio || 1, W = canvas.clientWidth, H = canvas.clientHeight;
    if (!W || !H) return;
    canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
    const ctx = canvas.getContext('2d'), v = fam.view;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H);
    const X = (x) => (x - v.x0) / (v.x1 - v.x0) * W, Y = (y) => (1 - (y - v.y0) / (v.y1 - v.y0)) * H;
    const path = (lines) => { ctx.beginPath(); for (const ln of lines) { ctx.moveTo(X(ln[0]), Y(ln[1])); for (let i = 2; i < ln.length; i += 2) ctx.lineTo(X(ln[i]), Y(ln[i + 1])); } };
    const reveal = opts.reveal == null ? 1 : opts.reveal;
    ctx.save(); ctx.beginPath(); ctx.rect(0, 0, W * reveal, H); ctx.clip();
    ctx.lineJoin = 'round'; ctx.lineCap = 'round';
    path([].concat(...fam.family)); ctx.strokeStyle = cssVar('--c-family'); ctx.globalAlpha = opts.alpha || .38; ctx.lineWidth = opts.lw || 1.1; ctx.stroke();
    ctx.globalAlpha = 1;
    if (opts.strong) { path(fam.sel); ctx.strokeStyle = cssVar('--plot-bg'); ctx.lineWidth = opts.strong + 3.5; ctx.stroke(); ctx.strokeStyle = cssVar('--c-family'); ctx.lineWidth = opts.strong; ctx.stroke(); }
    ctx.restore();
  }
  const THUMBS = { 1: 'h1-12', 2: 'h2-11', 3: 'h3-10' };
  let homeCleanup = null;

  /* Página de inicio: portada con curvas integrales y una tarjeta por hoja */
  function home() {
    if (observer) observer.disconnect();
    if (homeCleanup) homeCleanup();
    document.body.classList.add('is-home');
    const main = $('#hoja');
    $('.layout').classList.add('home');
    $('#indice').replaceChildren();
    const done = sheets.filter((s) => s.problems.length), total = sheets.reduce((n, s) => n + s.problems.length, 0);
    const heroCv = el('canvas', { class: 'hero-cv', 'aria-hidden': 'true' });
    const hero = el('section', { class: 'hero' }, heroCv,
      el('div', { class: 'hero-text' },
        el('h1', {}, site.name),
        el('p', { class: 'hero-course' }, site.course),
        el('p', { class: 'hero-sub' }, 'Ecuaciones diferenciales resueltas, con la gráfica de cada familia de soluciones: mueve las constantes y mira cómo cambia la curva.'),
        el('p', { class: 'hero-count' }, total + ' ejercicios resueltos en ' + done.length + (done.length === 1 ? ' hoja' : ' hojas'))));
    const thumbs = [];
    const cards = sheets.map((sh) => {
      const n = sh.problems.length;
      const tid = THUMBS[sh.n] || (sh.problems.find((p) => catalog[p.id] && catalog[p.id].kind === 'explicit') || {}).id;
      const cv = n && tid && catalog[tid] ? el('canvas', { class: 'thumb', 'aria-hidden': 'true' }) : el('div', { class: 'thumb blank', 'aria-hidden': 'true' });
      if (cv.tagName === 'CANVAS') thumbs.push([cv, catalog[tid]]);
      return el('a', { class: 'card' + (n ? '' : ' soon'), href: '#hoja-' + sh.n, 'aria-label': sh.title + (n ? ', ' + n + ' ejercicios' : ', próximamente') },
        cv,
        el('span', { class: 'card-body' },
          el('span', { class: 'card-title' }, sh.title),
          el('span', { class: 'card-meta' }, n ? n + (n === 1 ? ' ejercicio' : ' ejercicios') : 'Próximamente')));
    });
    main.replaceChildren(hero, el('section', { class: 'home' }, el('h2', { class: 'home-title' }, 'Elige una hoja'), el('div', { class: 'cards' }, ...cards)));
    window.scrollTo(0, 0);

    const heroSpec = catalog['h1-12'], fams = new Map();
    const famFor = (spec, n) => { const k = spec.id + n; if (!fams.has(k)) fams.set(k, familyOf(spec, n)); return fams.get(k); };
    const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
    let raf = 0, t0 = 0, finished = still;
    const drawHero = (r) => { if (heroSpec) paint(heroCv, famFor(heroSpec, 34), { reveal: r, strong: 3.2, lw: 1.2, alpha: .42 }); };
    const drawThumbs = () => thumbs.forEach(([cv, sp]) => paint(cv, famFor(sp, 15), { strong: 2.4, lw: 1, alpha: .5 }));
    const redraw = () => { drawHero(1); drawThumbs(); };
    if (still) redraw(); else {
      const step = (t) => { if (!t0) t0 = t; const k = Math.min(1, (t - t0) / 1700), e = 1 - Math.pow(1 - k, 3); drawHero(e); if (k < 1) raf = requestAnimationFrame(step); else finished = true; };
      requestAnimationFrame(() => { drawThumbs(); raf = requestAnimationFrame(step); });
    }
    const ro = new ResizeObserver(() => { if (finished) redraw(); else drawThumbs(); }); ro.observe(heroCv); thumbs.forEach(([cv]) => ro.observe(cv));
    const mo = new MutationObserver(redraw); mo.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    homeCleanup = () => { cancelAnimationFrame(raf); ro.disconnect(); mo.disconnect(); homeCleanup = null; };
  }

  function show(sheet) {
    if (observer) observer.disconnect();
    const main = $('#hoja'), idx = $('#indice');
    if (homeCleanup) homeCleanup();
    document.body.classList.remove('is-home');
    $('.layout').classList.remove('home');
    main.replaceChildren();
    if (!sheet.problems.length) {
      main.append(el('section', { class: 'empty' }, el('p', { class: 'soon-msg' }, 'Próximamente')));
      idx.replaceChildren();
      $('.layout').classList.add('home');
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
