/* Motor de expresiones y utilidades numéricas (equivalente a edoviz/expr.py).
 * La misma gramática y funciones que en Python:  + - * / ^  sin cos tan asin acos atan atan2 sinh cosh tanh
 * exp log(ln) log10 log2 sqrt cbrt abs sign floor ceil min max sec csc cot sel  y constantes pi e nan inf.
 */
(function (root) {
  'use strict';

  const H = {
    sin: Math.sin, cos: Math.cos, tan: Math.tan, asin: Math.asin, acos: Math.acos, atan: Math.atan, atan2: Math.atan2,
    sinh: Math.sinh, cosh: Math.cosh, tanh: Math.tanh, asinh: Math.asinh, acosh: Math.acosh, atanh: Math.atanh,
    exp: Math.exp, log: Math.log, log10: Math.log10, log2: Math.log2, sqrt: Math.sqrt, cbrt: Math.cbrt,
    abs: Math.abs, sign: Math.sign, floor: Math.floor, ceil: Math.ceil, min: Math.min, max: Math.max,
    sec: (x) => 1 / Math.cos(x), csc: (x) => 1 / Math.sin(x), cot: (x) => 1 / Math.tan(x),
    sel: (c, a, b) => (c > 0 ? a : b),
  };
  const ALIAS = { ln: 'log', sen: 'sin', tg: 'tan', arctan: 'atan', arcsin: 'asin', arccos: 'acos', sh: 'sinh',
                  ch: 'cosh', th: 'tanh', arcsen: 'asin', arctg: 'atan' };
  const CONSTS = { pi: 'Math.PI', e: 'Math.E', nan: 'NaN', inf: 'Infinity' };
  const TOKEN = /\s*(?:(\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+)|([A-Za-z_]\w*)|(\*\*|[-+*/^(),]))/y;

  function tokenize(src) {
    const s = src.trim(), out = [];
    TOKEN.lastIndex = 0;
    let pos = 0;
    while (pos < s.length) {
      TOKEN.lastIndex = pos;
      const m = TOKEN.exec(s);
      if (!m || m.index !== pos && s.slice(pos, m.index).trim() !== '') throw new Error('Carácter no válido en «' + src + '»');
      if (m[1] !== undefined) out.push(['num', m[1]]);
      else if (m[2] !== undefined) out.push(['name', m[2]]);
      else out.push(['op', m[3] === '**' ? '^' : m[3]]);
      pos = TOKEN.lastIndex;
    }
    return out;
  }

  class Parser {
    /* ctx: {vars:Set, consts:Map(nombre->índice en K), defs:Map(nombre->código)} */
    constructor(tokens, ctx) { this.t = tokens; this.i = 0; this.ctx = ctx; }
    peek() { return this.i < this.t.length ? this.t[this.i] : [null, null]; }
    eat(v) {
      const tok = this.peek();
      if (tok[0] === null || (v !== undefined && tok[1] !== v)) throw new Error('Se esperaba ' + v + ' y se encontró ' + tok[1]);
      this.i++; return tok;
    }
    expr() {
      let l = this.term();
      while (this.peek()[1] === '+' || this.peek()[1] === '-') { const op = this.eat()[1]; l = '(' + l + op + this.term() + ')'; }
      return l;
    }
    term() {
      let l = this.unary();
      while (this.peek()[1] === '*' || this.peek()[1] === '/') { const op = this.eat()[1]; l = '(' + l + op + this.unary() + ')'; }
      return l;
    }
    unary() {
      if (this.peek()[1] === '-' || this.peek()[1] === '+') { const op = this.eat()[1]; return '(' + op + this.unary() + ')'; }
      return this.power();
    }
    power() {
      const b = this.atom();
      if (this.peek()[1] === '^') { this.eat(); return 'Math.pow(' + b + ',' + this.unary() + ')'; }
      return b;
    }
    atom() {
      const [kind, val] = this.peek();
      if (kind === 'num') { this.eat(); return '(' + val + ')'; }
      if (kind === 'name') {
        this.eat();
        const name = ALIAS[val] || val;
        if (this.peek()[1] === '(') {
          if (!(name in H)) throw new Error('Función desconocida: ' + val);
          this.eat('(');
          const args = [];
          if (this.peek()[1] !== ')') { args.push(this.expr()); while (this.peek()[1] === ',') { this.eat(','); args.push(this.expr()); } }
          this.eat(')');
          return 'H.' + name + '(' + args.join(',') + ')';
        }
        if (this.ctx.vars.has(val)) return 'v_' + val;
        if (this.ctx.consts.has(val)) return 'K[' + this.ctx.consts.get(val) + ']';
        if (this.ctx.defs.has(val)) return this.ctx.defs.get(val);
        if (val in CONSTS) return CONSTS[val];
        throw new Error('Variable desconocida: «' + val + '»');
      }
      if (val === '(') { this.eat('('); const e = this.expr(); this.eat(')'); return '(' + e + ')'; }
      throw new Error('Expresión incompleta cerca de «' + val + '»');
    }
  }

  const cache = new Map();

  /* compile(texto, vars, constNames, defs) -> f(v1, v2, ..., K) donde K es el array de valores de las constantes. */
  function compile(text, vars, constNames, defs) {
    constNames = constNames || []; defs = defs || [];
    const key = text + '|' + vars.join(',') + '|' + constNames.join(',') + '|' + JSON.stringify(defs);
    if (cache.has(key)) return cache.get(key);
    const ctx = { vars: new Set(vars), consts: new Map(constNames.map((n, i) => [n, i])), defs: new Map() };
    for (const [dn, dt] of defs) {
      const p = new Parser(tokenize(String(dt)), ctx);
      ctx.defs.set(dn, '(' + p.expr() + ')');
    }
    const p = new Parser(tokenize(String(text)), ctx);
    const code = p.expr();
    if (p.i !== p.t.length) throw new Error('Sobran símbolos en «' + text + '»');
    const fn = new Function('H', 'return function(' + vars.map((v) => 'v_' + v).concat(['K']).join(',') + '){return ' + code + ';}')(H);
    cache.set(key, fn);
    return fn;
  }

  /* ---------------------------------------------------------------- curvas de nivel (marching squares) */
  const SEG = { 1: [[3, 0]], 2: [[0, 1]], 3: [[3, 1]], 4: [[1, 2]], 6: [[0, 2]], 7: [[3, 2]], 8: [[3, 2]], 9: [[0, 2]],
                11: [[1, 2]], 12: [[3, 1]], 13: [[0, 1]], 14: [[3, 0]] };

  function march(xs, ys, Z, L) {
    const nx = xs.length, ny = ys.length;
    const adj = new Map(), P = new Map();
    const link = (a, b) => {
      let la = adj.get(a); if (!la) adj.set(a, la = []); la.push(b);
      let lb = adj.get(b); if (!lb) adj.set(b, lb = []); lb.push(a);
    };
    for (let j = 0; j < ny - 1; j++) {
      for (let i = 0; i < nx - 1; i++) {
        const n = j * nx + i;
        const za = Z[n], zb = Z[n + 1], zc = Z[n + nx + 1], zd = Z[n + nx];
        if (za !== za || zb !== zb || zc !== zc || zd !== zd) continue;
        const idx = (za > L ? 1 : 0) | (zb > L ? 2 : 0) | (zc > L ? 4 : 0) | (zd > L ? 8 : 0);
        if (idx === 0 || idx === 15) continue;
        let segs;
        if (idx === 5 || idx === 10) {
          const hi = (za + zb + zc + zd) / 4 > L;
          segs = (idx === 5) === hi ? [[0, 1], [3, 2]] : [[3, 0], [1, 2]];
        } else segs = SEG[idx];
        const keyOf = [2 * n, 2 * (n + 1) + 1, 2 * (n + nx), 2 * n + 1];
        for (const [e1, e2] of segs) {
          for (const e of [e1, e2]) {
            const k = keyOf[e];
            if (P.has(k)) continue;
            let x, y, d;
            if (e === 0) { const t = (L - za) / (zb - za); x = xs[i] + t * (xs[i + 1] - xs[i]); y = ys[j]; d = Math.abs(zb - za); }
            else if (e === 1) { const t = (L - zb) / (zc - zb); x = xs[i + 1]; y = ys[j] + t * (ys[j + 1] - ys[j]); d = Math.abs(zc - zb); }
            else if (e === 2) { const t = (L - zd) / (zc - zd); x = xs[i] + t * (xs[i + 1] - xs[i]); y = ys[j + 1]; d = Math.abs(zc - zd); }
            else { const t = (L - za) / (zd - za); x = xs[i]; y = ys[j] + t * (ys[j + 1] - ys[j]); d = Math.abs(zd - za); }
            P.set(k, [x, y, d]);
          }
          link(keyOf[e1], keyOf[e2]);
        }
      }
    }
    // unir segmentos en polilíneas (primero las abiertas, luego los lazos)
    const seen = new Set(), lines = [];
    const walk = (start) => {
      const line = []; let prev = -1, cur = start;
      while (cur !== undefined && !seen.has(cur)) {
        seen.add(cur); line.push(P.get(cur));
        const nb = adj.get(cur); let next;
        for (const c of nb) if (c !== prev && !seen.has(c)) { next = c; break; }
        prev = cur; cur = next;
      }
      if (line.length > 1 && adj.get(start) && adj.get(start).length === 2 && start !== cur) { /* lazo cerrado: cerrar */ }
      return line;
    };
    for (const [k, nb] of adj) if (nb.length === 1 && !seen.has(k)) lines.push(walk(k));
    for (const [k, nb] of adj) if (!seen.has(k)) { const ln = walk(k); if (ln.length > 2) ln.push(ln[0]); lines.push(ln); }
    return lines;
  }

  /* Quita vértices que no son cruces reales (polos de F): F(q) debe ser ≈ nivel. */
  function cleanLine(line, L, F, K) {
    const out = []; let cur = [];
    for (const [x, y, d] of line) {
      const f = F(x, y, K);
      const ok = Number.isFinite(f) && Math.abs(f - L) <= 0.2 * d + 1e-9 * (1 + Math.abs(L));
      if (ok) cur.push(x, y); else { if (cur.length >= 4) out.push(cur); cur = []; }
    }
    if (cur.length >= 4) out.push(cur);
    return out;
  }

  function levelGrid(F, K, view, nx, ny) {
    const xs = new Float64Array(nx), ys = new Float64Array(ny), Z = new Float64Array(nx * ny);
    for (let i = 0; i < nx; i++) xs[i] = view.x0 + (view.x1 - view.x0) * i / (nx - 1);
    for (let j = 0; j < ny; j++) ys[j] = view.y0 + (view.y1 - view.y0) * j / (ny - 1);
    for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
      const z = F(xs[i], ys[j], K);
      Z[j * nx + i] = Number.isFinite(z) && Math.abs(z) < 1e8 ? z : NaN;
    }
    return { xs, ys, Z };
  }

  function contourLines(grid, L, F, K) {
    const res = [];
    for (const ln of march(grid.xs, grid.ys, grid.Z, L)) res.push(...cleanLine(ln, L, F, K));
    return res;
  }

  /* Corta una curva muestreada en trazos continuos (NaN, fuera de ventana, polos). Devuelve arrays planos [x,y,...]. */
  function splitCurve(X, Y, view) {
    const W = view.x1 - view.x0, Hh = view.y1 - view.y0, cx = (view.x0 + view.x1) / 2, cy = (view.y0 + view.y1) / 2;
    const out = []; let cur = [];
    const flush = () => { if (cur.length >= 4) out.push(cur); cur = []; };
    for (let i = 0; i < X.length; i++) {
      const x = X[i], y = Y[i];
      const bad = !Number.isFinite(x) || !Number.isFinite(y) || Math.abs(y - cy) > 3 * Hh || Math.abs(x - cx) > 3 * W;
      if (bad) { flush(); continue; }
      if (cur.length) {
        const px = cur[cur.length - 2], py = cur[cur.length - 1];
        if (Math.abs(x - px) > 1.5 * W || Math.abs(y - py) > 1.5 * Hh) flush();
      }
      cur.push(x, y);
    }
    flush();
    return out;
  }

  /* Muestrea y=f(x) y añade por bisección el punto exacto donde f deja de estar definida
     (une las ramas ±sqrt(...) en la tangente vertical sin hueco). Devuelve {X, Y}. */
  function sampleExplicit(f, valid, K, X0) {
    const val = (x) => { if (valid && !(valid(x, K) >= 0)) return NaN; return f(x, K); };
    let X = X0; const ok = Array.from(X0, (x) => Number.isFinite(val(x)));
    const extra = [];
    for (let i = 0; i < X0.length - 1; i++) {
      if (ok[i] === ok[i + 1]) continue;
      let lo = ok[i] ? X0[i] : X0[i + 1], hi = ok[i] ? X0[i + 1] : X0[i];
      for (let k = 0; k < 60; k++) { const m = (lo + hi) / 2; if (Number.isFinite(val(m))) lo = m; else hi = m; }
      extra.push(lo);
    }
    if (extra.length) { X = Float64Array.from(Array.from(X0).concat(extra)).sort(); }
    const Y = new Float64Array(X.length);
    for (let i = 0; i < X.length; i++) Y[i] = val(X[i]);
    return { X, Y };
  }

  /* sweep de una constante (misma lógica que edoviz.plotting.sweep_values) */
  function sweepValues(c) {
    const out = []; const lo = c.min, hi = c.max, n = c.n || 13;
    if (c.integer) { for (let v = Math.round(lo); v <= Math.round(hi); v++) out.push(v); return out; }
    if (c.spacing === 'geom' && lo > 0) { for (let i = 0; i < n; i++) out.push(lo * Math.pow(hi / lo, i / (n - 1))); return out; }
    if (c.spacing === 'symlog') {
      const m = Math.max(Math.abs(lo), Math.abs(hi)), h = Math.max(Math.floor(n / 2), 2), pos = [];
      for (let i = 0; i < h; i++) pos.push(m * 1e-3 * Math.pow(1e3, i / (h - 1)));
      return pos.map((v) => -v).reverse().concat(pos);
    }
    for (let i = 0; i < n; i++) out.push(lo + (hi - lo) * i / (n - 1));
    return out;
  }

  /* cortes entre dos conjuntos de polilíneas planas (marca de la ortogonalidad) */
  function intersections(A, B, limit) {
    limit = limit || 300;
    const segs = (lines) => {
      const s = [];
      for (const ln of lines) {
        const m = ln.length / 2, step = Math.max(1, Math.floor(m / limit));
        for (let k = 0; k + step < m; k += step) s.push([ln[2 * k], ln[2 * k + 1], ln[2 * (k + step)], ln[2 * (k + step) + 1]]);
      }
      return s;
    };
    const sa = segs(A), sb = segs(B), pts = [];
    for (const a of sa) {
      const rx = a[2] - a[0], ry = a[3] - a[1];
      for (const b of sb) {
        const sx = b[2] - b[0], sy = b[3] - b[1], den = rx * sy - ry * sx;
        if (Math.abs(den) < 1e-14) continue;
        const qx = b[0] - a[0], qy = b[1] - a[1];
        const t = (qx * sy - qy * sx) / den, u = (qx * ry - qy * rx) / den;
        if (t >= 0 && t <= 1 && u >= 0 && u <= 1) pts.push([a[0] + t * rx, a[1] + t * ry]);
      }
    }
    return pts;
  }

  const api = { compile, tokenize, march, cleanLine, levelGrid, contourLines, splitCurve, sampleExplicit, sweepValues, intersections, H };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.EdoEngine = api;
})(typeof window !== 'undefined' ? window : globalThis);
