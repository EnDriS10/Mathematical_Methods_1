/* Gráfico interactivo de una familia de soluciones (canvas 2D).
 *   const p = new EdoPlot(contenedor, spec);   // spec = entrada de data/catalog.json
 * Sliders por constante · curva elegida en trazo grueso · clic = curva por ese punto · rueda = zoom · arrastrar = mover.
 */
(function () {
  'use strict';
  const E = window.EdoEngine;
  const NS = 'http://www.w3.org/2000/svg';

  const fmt = (v) => {
    if (!Number.isFinite(v)) return String(v);
    const a = Math.abs(v);
    if (a !== 0 && (a >= 1e4 || a < 1e-3)) return v.toExponential(2);
    return String(parseFloat(v.toPrecision(4)));
  };
  const niceStep = (span, target) => {
    const raw = span / target, mag = Math.pow(10, Math.floor(Math.log10(raw))), f = raw / mag;
    return (f < 1.5 ? 1 : f < 3.5 ? 2 : f < 7.5 ? 5 : 10) * mag;
  };
  const el = (tag, attrs, ...kids) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (k === 'class') n.className = v; else if (k.startsWith('on')) n.addEventListener(k.slice(2), v);
      else if (v !== false && v != null) n.setAttribute(k, v === true ? '' : v);
    }
    for (const kid of kids) n.append(kid);
    return n;
  };

  class EdoPlot {
    constructor(root, spec) {
      this.spec = spec;
      this.root = root;
      this.cn = spec.consts.map((c) => c.name);
      this.levelNames = spec.consts.filter((c) => c.role === 'level').map((c) => c.name);
      this.defs = spec.defs || [];
      this.env = {}; spec.consts.forEach((c) => (this.env[c.name] = c.value));
      this.opts = { family: true, field: false, extras: true, particular: true };
      this.view = null;
      this.cache = {};
      this.compileAll();
      this.build();
      this.resetView();
      this.draw();
      this._ro = new ResizeObserver(() => { this.resize(); this.draw(); });
      this._ro.observe(this.stage);
      this._mo = new MutationObserver(() => this.draw());
      this._mo.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
      matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => this.draw());
    }

    /* ------------------------------------------------------------ compilación */
    fn(text, vars) { return E.compile(String(text), vars, this.cn, this.defs); }
    compileCurve(c, fallbackKind) {
      const kind = c.kind || fallbackKind, o = { kind, label: c.label };
      if (kind === 'explicit') { o.ys = (Array.isArray(c.y) ? c.y : [c.y]).map((t) => this.fn(t, ['x'])); if (c.valid) o.valid = this.fn(c.valid, ['x']); }
      else if (kind === 'vline') o.xf = this.fn(c.x, ['x']);
      else if (kind === 'param') { o.var = c.var; o.t = c.t; o.xf = this.fn(c.x, [c.var]); o.yf = this.fn(c.y, [c.var]); }
      else if (kind === 'level') { o.F = this.fn(c.F, ['x', 'y']); o.c = this.fn(c.c, ['x']); }
      return o;
    }
    compileAll() {
      const s = this.spec;
      if (s.kind === 'level') this.F = this.fn(s.F, ['x', 'y']);
      if (s.kind === 'ortho') { this.F1 = this.fn(s.main.F, ['x', 'y']); this.F2 = this.fn(s.ortho.F, ['x', 'y']); }
      if (s.kind === 'explicit' || s.kind === 'param') {
        this.main = this.compileCurve(Object.assign({ kind: s.kind }, s, { label: null }), s.kind);
        if (s.valid) this.main.valid = this.fn(s.valid, ['x']);
      }
      this.extras = (s.extras || []).map((c) => this.compileCurve(c, 'explicit'));
      this.slope = s.slope ? this.fn(s.slope, ['x', 'y']) : null;
      if (s.particular) {
        const p = s.particular;
        this.part = { label: p.label, values: p.values || null, curve: p.curve ? this.compileCurve(p.curve, 'explicit') : null,
                      px: p.point ? this.fn(p.point[0], ['x']) : null, py: p.point ? this.fn(p.point[1], ['x']) : null };
      }
    }
    K(env) { return this.cn.map((n) => (env || this.env)[n]); }

    /* ------------------------------------------------------------ interfaz */
    build() {
      const s = this.spec, root = this.root;
      root.classList.add('edo-plot');
      this.stage = el('div', { class: 'stage' });
      this.canvas = el('canvas', { class: 'cv', role: 'img', 'aria-label': 'Gráfico de la familia de soluciones' });
      this.readout = el('div', { class: 'readout', 'aria-hidden': 'true' });
      this.stage.append(this.canvas, this.readout);
      this.legend = el('ul', { class: 'legend' });
      this.controls = el('div', { class: 'controls' });
      const tools = el('div', { class: 'tools' });
      const chip = (key, text) => {
        const id = 'c' + Math.random().toString(36).slice(2, 8);
        const input = el('input', { type: 'checkbox', id, checked: this.opts[key] });
        input.addEventListener('change', () => { this.opts[key] = input.checked; this.draw(); });
        return el('label', { class: 'chip', for: id }, input, el('span', {}, text));
      };
      tools.append(chip('family', 'Todas las curvas'));
      if (this.slope) { this.opts.field = false; tools.append(chip('field', 'Campo de direcciones')); }
      if ((s.extras || []).length) tools.append(chip('extras', 'Soluciones singulares'));
      if (s.particular) tools.append(chip('particular', 'Solución particular'));
      this.sliders = {};
      for (const c of s.consts) this.controls.append(this.makeSlider(c));
      const actions = el('div', { class: 'actions' });
      if (s.particular && s.particular.values) actions.append(el('button', { type: 'button', onclick: () => this.setValues(s.particular.values) }, 'Ir a la particular'));
      actions.append(
        el('button', { type: 'button', onclick: () => { s.consts.forEach((c) => (this.env[c.name] = c.value)); this.syncSliders(); this.resetView(); this.draw(); } }, 'Restablecer'),
        el('button', { type: 'button', onclick: () => this.download() }, 'Descargar PNG'));
      const hint = this.canPick() ? el('p', { class: 'hint' }, 'Haz clic en el gráfico para elegir la curva que pasa por ese punto. Rueda para ampliar, arrastra para mover.')
                                 : el('p', { class: 'hint' }, 'Rueda para ampliar, arrastra para mover.');
      root.append(this.stage, this.legend, tools, this.controls, actions, hint);
      this.bindPointer();
      this.resize();
    }
    makeSlider(c) {
      const id = 's' + Math.random().toString(36).slice(2, 8);
      const range = el('input', { type: 'range', id, min: c.min, max: c.max, step: c.step || 'any', value: c.value, 'aria-label': 'Constante ' + c.name });
      const num = el('input', { type: 'number', step: c.step || 'any', value: c.value, class: 'num', 'aria-label': c.name + ' (valor)' });
      const set = (v) => { if (!Number.isFinite(v)) return; this.env[c.name] = c.integer ? Math.round(v) : v; this.draw(); };
      range.addEventListener('input', () => { num.value = fmt(+range.value); set(+range.value); });
      num.addEventListener('input', () => { range.value = num.value; set(+num.value); });
      this.sliders[c.name] = { range, num };
      return el('div', { class: 'row' }, el('label', { for: id, class: 'name' }, c.label || c.name), range, num);
    }
    syncSliders() { for (const c of this.spec.consts) { const s = this.sliders[c.name]; s.range.value = this.env[c.name]; s.num.value = fmt(this.env[c.name]); } }
    setValues(vals) { Object.assign(this.env, vals); this.syncSliders(); this.draw(); }

    resize() {
      const w = Math.max(240, this.stage.clientWidth || 480);
      const win = this.spec.window, ratio = (win[3] - win[2]) / (win[1] - win[0]);
      const r = this.spec.aspect === 'equal' ? Math.min(1.05, Math.max(0.6, ratio)) : 0.72;
      this.cssW = w; this.cssH = Math.round(w * r);
      const dpr = window.devicePixelRatio || 1;
      this.canvas.width = Math.round(this.cssW * dpr); this.canvas.height = Math.round(this.cssH * dpr);
      this.canvas.style.height = this.cssH + 'px';
      this.dpr = dpr;
      this.cache = {};
      if (this.view) this.fitAspect();
    }
    resetView() { const w = this.spec.window; this.view = { x0: w[0], x1: w[1], y0: w[2], y1: w[3] }; this.fitAspect(); this.cache = {}; }
    fitAspect() {
      if (this.spec.aspect !== 'equal') return;
      const v = this.view, W = this.cssW, Hh = this.cssH;
      const ppu = Math.min(W / (v.x1 - v.x0), Hh / (v.y1 - v.y0));
      const cx = (v.x0 + v.x1) / 2, cy = (v.y0 + v.y1) / 2, hw = W / ppu / 2, hh = Hh / ppu / 2;
      Object.assign(v, { x0: cx - hw, x1: cx + hw, y0: cy - hh, y1: cy + hh });
    }
    X(x) { return (x - this.view.x0) / (this.view.x1 - this.view.x0) * this.cssW; }
    Y(y) { return (1 - (y - this.view.y0) / (this.view.y1 - this.view.y0)) * this.cssH; }
    ux(px) { return this.view.x0 + px / this.cssW * (this.view.x1 - this.view.x0); }
    uy(py) { return this.view.y0 + (1 - py / this.cssH) * (this.view.y1 - this.view.y0); }

    /* ------------------------------------------------------------ geometría de las curvas */
    curveLines(c, env) {
      const K = this.K(env), v = this.view, out = [];
      if (c.kind === 'explicit') {
        const n = Math.round(this.cssW * 2.2), X = new Float64Array(n);
        for (let i = 0; i < n; i++) X[i] = v.x0 + (v.x1 - v.x0) * i / (n - 1);
        for (const f of c.ys) {
          const Y = new Float64Array(n);
          for (let i = 0; i < n; i++) { const ok = !c.valid || c.valid(X[i], K) >= 0; Y[i] = ok ? f(X[i], K) : NaN; }
          out.push(...E.splitCurve(X, Y, v));
        }
      } else if (c.kind === 'vline') {
        const x = c.xf(0, K); if (Number.isFinite(x)) out.push([x, v.y0, x, v.y1]);
      } else if (c.kind === 'param') {
        for (const [lo, hi] of c.t) {
          const n = 3000, X = new Float64Array(n), Y = new Float64Array(n);
          for (let i = 0; i < n; i++) { const t = lo + (hi - lo) * i / (n - 1); X[i] = c.xf(t, K); Y[i] = c.yf(t, K); }
          out.push(...E.splitCurve(X, Y, v));
        }
      } else if (c.kind === 'level') {
        const nx = 260, ny = 260, g = E.levelGrid(c.F, K, v, nx, ny), L = c.c(0, K);
        out.push(...E.contourLines(g, L, c.F, K));
      }
      return out;
    }
    grid(tag, F, env, skip) {
      const v = this.view, K = this.K(env);
      const key = [tag, v.x0, v.x1, v.y0, v.y1, this.cssW, this.cn.map((n) => (skip.includes(n) ? '' : env[n])).join(',')].join('|');
      if (!this.cache[key]) {
        for (const k of Object.keys(this.cache)) if (k.startsWith(tag + '|')) delete this.cache[k];
        const side = Math.min(320, Math.max(160, Math.round(this.cssW * 0.65)));
        this.cache[key] = { grid: E.levelGrid(F, K, v, side, Math.round(side * this.cssH / this.cssW)), fam: new Map() };
      }
      return this.cache[key];
    }
    levelFamily(tag, F, lc, env) {
      const entry = this.grid(tag, F, env, this.levelNames);
      const K = this.K(env), lines = [];
      if (this.opts.family) for (const L of E.sweepValues(lc)) {
        if (!entry.fam.has(L)) entry.fam.set(L, E.contourLines(entry.grid, L, F, K));
        lines.push(...entry.fam.get(L));
      }
      return { entry, family: lines, sel: E.contourLines(entry.grid, env[lc.name], F, K) };
    }

    /* ------------------------------------------------------------ dibujo */
    theme() {
      const cs = getComputedStyle(this.root), g = (n) => cs.getPropertyValue(n).trim();
      return { bg: g('--plot-bg'), grid: g('--plot-grid'), axis: g('--plot-axis'), text: g('--plot-text'), fam: g('--c-family'),
               ort: g('--c-ortho'), ext: g('--c-extra'), par: g('--c-particular'), field: g('--plot-field'), halo: g('--plot-bg') };
    }
    path(ctx, lines) {
      ctx.beginPath();
      for (const ln of lines) { ctx.moveTo(this.X(ln[0]), this.Y(ln[1])); for (let i = 2; i < ln.length; i += 2) ctx.lineTo(this.X(ln[i]), this.Y(ln[i + 1])); }
    }
    stroke(ctx, lines, color, w, dash, alpha) {
      this.path(ctx, lines); ctx.strokeStyle = color; ctx.lineWidth = w; ctx.setLineDash(dash || []); ctx.globalAlpha = alpha == null ? 1 : alpha; ctx.stroke(); ctx.globalAlpha = 1;
    }
    strong(ctx, lines, color, w, th) { this.stroke(ctx, lines, th.halo, w + 3.4); this.stroke(ctx, lines, color, w); }

    axes(ctx, th) {
      const v = this.view, W = this.cssW, Hh = this.cssH;
      ctx.fillStyle = th.bg; ctx.fillRect(0, 0, W, Hh);
      ctx.font = '11px ui-sans-serif, system-ui, sans-serif'; ctx.lineWidth = 1;
      const sx = niceStep(v.x1 - v.x0, W / 70), sy = niceStep(v.y1 - v.y0, Hh / 55);
      ctx.strokeStyle = th.grid; ctx.beginPath();
      for (let x = Math.ceil(v.x0 / sx) * sx; x <= v.x1; x += sx) { const px = Math.round(this.X(x)) + .5; ctx.moveTo(px, 0); ctx.lineTo(px, Hh); }
      for (let y = Math.ceil(v.y0 / sy) * sy; y <= v.y1; y += sy) { const py = Math.round(this.Y(y)) + .5; ctx.moveTo(0, py); ctx.lineTo(W, py); }
      ctx.stroke();
      ctx.strokeStyle = th.axis; ctx.lineWidth = 1.2; ctx.beginPath();
      if (v.x0 < 0 && v.x1 > 0) { const px = Math.round(this.X(0)) + .5; ctx.moveTo(px, 0); ctx.lineTo(px, Hh); }
      if (v.y0 < 0 && v.y1 > 0) { const py = Math.round(this.Y(0)) + .5; ctx.moveTo(0, py); ctx.lineTo(W, py); }
      ctx.stroke();
      ctx.fillStyle = th.text; ctx.textAlign = 'center'; ctx.textBaseline = 'bottom';
      const ty = Math.min(Hh - 3, Math.max(14, v.y0 < 0 && v.y1 > 0 ? this.Y(0) + 14 : Hh - 3));
      for (let x = Math.ceil(v.x0 / sx) * sx; x <= v.x1; x += sx) if (Math.abs(x) > sx / 1e3) ctx.fillText(fmt(+x.toFixed(10)), this.X(x), ty > Hh - 3 ? Hh - 3 : ty + (ty < Hh - 3 && v.y0 < 0 && v.y1 > 0 ? 0 : 0));
      ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
      const tx = v.x0 < 0 && v.x1 > 0 ? Math.min(W - 30, this.X(0) + 4) : 4;
      for (let y = Math.ceil(v.y0 / sy) * sy; y <= v.y1; y += sy) if (Math.abs(y) > sy / 1e3) ctx.fillText(fmt(+y.toFixed(10)), tx, this.Y(y) - 7);
    }

    draw() {
      if (this._raf) return;
      this._raf = requestAnimationFrame(() => { this._raf = 0; this.render(); });
    }
    render() {
      const s = this.spec, ctx = this.canvas.getContext('2d'), th = this.theme(), env = this.env, leg = [];
      ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
      this.axes(ctx, th);
      ctx.save(); ctx.beginPath(); ctx.rect(0, 0, this.cssW, this.cssH); ctx.clip();
      try {
        if (this.opts.field && this.slope) this.drawField(ctx, th);
        if (s.kind === 'level') {
          const lc = s.consts.find((c) => c.role === 'level');
          const r = this.levelFamily('F', this.F, lc, env);
          if (this.opts.family) { this.stroke(ctx, r.family, th.fam, 1, null, 0.4); leg.push([th.fam, 'familia (' + lc.name + ' variable)', 1, .6]); }
          this.strong(ctx, r.sel, th.fam, 3, th); leg.push([th.fam, lc.name + ' = ' + fmt(env[lc.name]), 3]);
        } else if (s.kind === 'ortho') {
          const c1 = s.consts.find((c) => c.name === s.main.level), c2 = s.consts.find((c) => c.name === s.ortho.level);
          const r1 = this.levelFamily('F1', this.F1, c1, env), r2 = this.levelFamily('F2', this.F2, c2, env);
          if (this.opts.family) { this.stroke(ctx, r1.family, th.fam, 1, null, 0.4); this.stroke(ctx, r2.family, th.ort, 1, null, 0.4); }
          this.strong(ctx, r1.sel, th.fam, 3, th); this.strong(ctx, r2.sel, th.ort, 3, th);
          leg.push([th.fam, 'principal (' + c1.name + ' = ' + fmt(env[c1.name]) + ')', 3], [th.ort, 'ortogonal (' + c2.name + ' = ' + fmt(env[c2.name]) + ')', 3]);
          const pts = E.intersections(r1.sel, r2.sel);
          ctx.fillStyle = th.text; ctx.strokeStyle = th.bg; ctx.lineWidth = 2;
          for (const [x, y] of pts) { ctx.beginPath(); ctx.arc(this.X(x), this.Y(y), 4.2, 0, 6.2832); ctx.stroke(); ctx.fill(); }
          if (pts.length) leg.push([th.text, 'cortes: ángulo de 90°', 'dot']);
        } else {
          if (this.opts.family) {
            for (const c of s.consts) {
              if (c.sweep === false || c.role === 'level') continue;
              for (const val of E.sweepValues(c)) { const e2 = Object.assign({}, env, { [c.name]: val }); this.stroke(ctx, this.curveLines(this.main, e2), th.fam, 1, null, 0.4); }
            }
            leg.push([th.fam, 'familia (constantes variables)', 1, .6]);
          }
          this.strong(ctx, this.curveLines(this.main, env), th.fam, 3, th);
          const shown = s.consts.filter((c) => c.sweep !== false && c.role !== 'level').map((c) => c.name + ' = ' + fmt(env[c.name])).join(', ');
          leg.push([th.fam, 'curva elegida (' + shown + ')', 3]);
        }
        if (this.opts.extras && this.extras.length) {
          for (const c of this.extras) this.stroke(ctx, this.curveLines(c, env), th.ext, 1.8, [6, 4]);
          const labels = this.extras.map((c) => c.label).filter(Boolean);
          if (labels.length) leg.push([th.ext, 'singulares: ' + labels.join(' · '), 1.8, 1, true]);
        }
        if (this.opts.particular && this.part) this.drawParticular(ctx, th, leg);
      } catch (err) { console.error(this.spec.id, err); }
      ctx.restore();
      this.renderLegend(leg);
    }
    drawParticular(ctx, th, leg) {
      const s = this.spec, p = this.part, env = this.env;
      let lines;
      if (p.values) {
        const e2 = Object.assign({}, env, p.values);
        if (s.kind === 'level') {
          const lc = s.consts.find((c) => c.role === 'level'), K = this.K(e2), g = this.grid('F', this.F, e2, this.levelNames).grid;
          lines = E.contourLines(g, e2[lc.name], this.F, K);
        } else lines = this.curveLines(this.main, e2);
      } else lines = this.curveLines(p.curve, env);
      this.strong(ctx, lines, th.par, 3.4, th);
      if (p.px) {
        const K = this.K(env), x = p.px(0, K), y = p.py(0, K);
        if (Number.isFinite(x) && Number.isFinite(y)) { ctx.beginPath(); ctx.arc(this.X(x), this.Y(y), 5.5, 0, 6.2832); ctx.fillStyle = th.par; ctx.fill(); ctx.strokeStyle = th.bg; ctx.lineWidth = 2; ctx.stroke(); }
      }
      leg.push([th.par, 'solución particular: ' + (p.label || ''), 3.4]);
    }
    drawField(ctx, th) {
      const v = this.view, K = this.K(), nx = 26, ny = 18, len = Math.min(this.cssW / nx, this.cssH / ny) * 0.42;
      ctx.strokeStyle = th.field; ctx.lineWidth = 1.2; ctx.globalAlpha = .75; ctx.beginPath();
      for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
        const x = v.x0 + (i + .5) / nx * (v.x1 - v.x0), y = v.y0 + (j + .5) / ny * (v.y1 - v.y0), m = this.slope(x, y, K);
        if (!Number.isFinite(m)) continue;
        const ppx = this.cssW / (v.x1 - v.x0), ppy = this.cssH / (v.y1 - v.y0);
        const dx = 1 * ppx, dy = -m * ppy, n = Math.hypot(dx, dy) || 1, ux = dx / n * len, uy = dy / n * len, px = this.X(x), py = this.Y(y);
        ctx.moveTo(px - ux, py - uy); ctx.lineTo(px + ux, py + uy);
      }
      ctx.stroke(); ctx.globalAlpha = 1;
    }
    renderLegend(items) {
      this.legend.replaceChildren(...items.map(([color, text, w, a, dashed]) => {
        const sw = el('span', { class: 'sw' + (w === 'dot' ? ' dot' : '') });
        sw.style.setProperty('--sw', color);
        if (w !== 'dot') { sw.style.height = Math.max(2, Math.min(w, 4)) + 'px'; if (a) sw.style.opacity = a; if (dashed) sw.classList.add('dashed'); }
        return el('li', {}, sw, el('span', {}, text));
      }));
    }

    /* ------------------------------------------------------------ ratón / táctil */
    canPick() {
      const k = this.spec.kind;
      if (k === 'level' || k === 'ortho') return true;
      return this.pickConst() != null;
    }
    pickConst() {
      const c = this.spec.consts.filter((c) => c.sweep !== false && !c.integer && c.role !== 'level');
      return c.length === 1 ? c[0] : null;
    }
    pick(x, y) {
      const s = this.spec, K = this.K();
      const clamp = (c, v) => Math.min(c.max, Math.max(c.min, v));
      if (s.kind === 'level') {
        const lc = s.consts.find((c) => c.role === 'level'), v = this.F(x, y, K);
        if (Number.isFinite(v)) this.env[lc.name] = clamp(lc, v);
      } else if (s.kind === 'ortho') {
        const c1 = s.consts.find((c) => c.name === s.main.level), c2 = s.consts.find((c) => c.name === s.ortho.level);
        const a = this.F1(x, y, K), b = this.F2(x, y, K);
        if (Number.isFinite(a)) this.env[c1.name] = clamp(c1, a);
        if (Number.isFinite(b)) this.env[c2.name] = clamp(c2, b);
      } else {
        const c = this.pickConst(); if (!c) return;
        const sx = (this.view.x1 - this.view.x0), sy = (this.view.y1 - this.view.y0);
        const dist = (val) => {
          const e2 = Object.assign({}, this.env, { [c.name]: val });
          let best = Infinity;
          for (const ln of this.curveLines(this.main, e2)) for (let i = 0; i < ln.length; i += 2) {
            const d = ((ln[i] - x) / sx) ** 2 + ((ln[i + 1] - y) / sy) ** 2; if (d < best) best = d;
          }
          return best;
        };
        let bestV = this.env[c.name], bestD = Infinity; const N = 120;
        for (let i = 0; i <= N; i++) { const val = c.min + (c.max - c.min) * i / N, d = dist(val); if (d < bestD) { bestD = d; bestV = val; } }
        let lo = Math.max(c.min, bestV - (c.max - c.min) / N), hi = Math.min(c.max, bestV + (c.max - c.min) / N);
        for (let it = 0; it < 28; it++) { const m1 = lo + (hi - lo) / 3, m2 = hi - (hi - lo) / 3; if (dist(m1) < dist(m2)) hi = m2; else lo = m1; }
        this.env[c.name] = (lo + hi) / 2;
      }
      this.syncSliders(); this.draw();
    }
    bindPointer() {
      const cv = this.canvas; let drag = null; const pts = new Map();
      const pos = (e) => { const r = cv.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
      cv.style.touchAction = 'none';
      cv.addEventListener('pointerdown', (e) => { cv.setPointerCapture(e.pointerId); const [px, py] = pos(e); drag = { px, py, v: Object.assign({}, this.view), moved: false }; });
      cv.addEventListener('pointermove', (e) => {
        const [px, py] = pos(e);
        this.readout.textContent = 'x = ' + fmt(this.ux(px)) + '   y = ' + fmt(this.uy(py)); this.readout.style.opacity = 1;
        if (!drag) return;
        const dx = px - drag.px, dy = py - drag.py;
        if (Math.hypot(dx, dy) > 4) drag.moved = true;
        if (drag.moved) {
          const wx = (drag.v.x1 - drag.v.x0) / this.cssW, wy = (drag.v.y1 - drag.v.y0) / this.cssH;
          this.view = { x0: drag.v.x0 - dx * wx, x1: drag.v.x1 - dx * wx, y0: drag.v.y0 + dy * wy, y1: drag.v.y1 + dy * wy }; this.draw();
        }
      });
      cv.addEventListener('pointerup', (e) => { if (drag && !drag.moved) { const [px, py] = pos(e); this.pick(this.ux(px), this.uy(py)); } drag = null; });
      cv.addEventListener('pointerleave', () => { this.readout.style.opacity = 0; });
      cv.addEventListener('wheel', (e) => {
        e.preventDefault(); const [px, py] = pos(e), f = Math.exp(Math.sign(e.deltaY) * 0.15), x = this.ux(px), y = this.uy(py), v = this.view;
        this.view = { x0: x - (x - v.x0) * f, x1: x + (v.x1 - x) * f, y0: y - (y - v.y0) * f, y1: y + (v.y1 - y) * f }; this.draw();
      }, { passive: false });
      cv.addEventListener('dblclick', () => { this.resetView(); this.draw(); });
    }
    download() {
      this.render();
      this.canvas.toBlob((b) => { const a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = (this.spec.id || 'grafica') + '.png'; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000); });
    }
  }
  window.EdoPlot = EdoPlot;
})();
