"""Funciones de graficado (matplotlib) para familias de soluciones de EDOs.

Uso típico (todo son funciones; solo hay que llamarlas)::

    from edoviz import plot_problem, plot_level, plot_explicit, plot_param, plot_orthogonal, plot_ode

    plot_problem("h3-17")                                  # un problema del catálogo
    plot_level("atan(x)+atan(y)", C=(-3, 3, 0.8))          # solución implícita F(x,y)=C
    plot_explicit("exp(-x)+C*exp(-2*x)", C=(-3, 3, 1))     # solución explícita y=f(x;C)
    plot_param("(p+1)*exp(p)+C", "p^2*exp(p)", "p", (-10, 2), C=(-4, 4, 0))
    plot_orthogonal("y/x^2", "x^2+2*y^2", a=(-3, 3, 1), C=(0.5, 12, 4))
    plot_ode(slope="sin(x-y)")                             # solo la EDO: integración numérica

Cada constante se da como ``(mín, máx, valor)``: el rango se muestrea (todas las
curvas posibles, en trazo fino) y la curva con ``valor`` se resalta (trazo grueso).
"""
from __future__ import annotations

import functools
import math
import re
from typing import Iterable, Mapping, Sequence

import matplotlib.pyplot as plt
import numpy as np
from contourpy import contour_generator

from . import catalog
from .expr import compile_expr, free_names

# --------------------------------------------------------------------------- estilo
THEMES = {
    "light": dict(bg="#fcfcfb", fg="#0b0b0b", muted="#52514e", grid="#e6e5e1", axis="#a9a8a2",
                  family="#2a78d6", ortho="#eb6834", extra="#4a3aa7", particular="#008300", field="#9a9992"),
    "print": dict(bg="#ffffff", fg="#000000", muted="#444444", grid="#e3e3e3", axis="#8a8a8a",
                  family="#1f65bd", ortho="#e0561f", extra="#4a3aa7", particular="#007a00", field="#8c8c8c"),
    "dark": dict(bg="#1a1a19", fg="#ffffff", muted="#c3c2b7", grid="#2e2e2c", axis="#6d6c66",
                 family="#3987e5", ortho="#d95926", extra="#9085e9", particular="#3fae49", field="#7a7972"),
}


def _tex(s: str) -> str:
    """TeX de LaTeX completo -> TeX que entiende matplotlib.mathtext."""
    for a, b in (("\\dfrac", "\\frac"), ("\\tfrac", "\\frac"), ("\\;", "\\ "), ("\\,", "\\ ")):
        s = s.replace(a, b)
    return s


# --------------------------------------------------------------------------- resultado (se muestra solo en Jupyter)
def _in_notebook() -> bool:
    try:
        ip = get_ipython()  # type: ignore[name-defined]  # noqa: F821
        return "IPKernelApp" in ip.config
    except Exception:
        return False


class PlotResult(tuple):
    """``(fig, ax)`` que además se dibuja solo al ser la última línea de una celda de Jupyter."""

    def _repr_png_(self):
        import io
        buf = io.BytesIO()
        fig = self[0]
        fig.savefig(buf, format="png", dpi=110, bbox_inches="tight", facecolor=fig.get_facecolor())
        return buf.getvalue()

    def __repr__(self):
        return "<edoviz.PlotResult>" if _in_notebook() else tuple.__repr__(self)


def _finish(fig, ax, created=True):
    if created and _in_notebook():
        plt.close(fig)          # evita que el backend inline lo dibuje por segunda vez
    return PlotResult((fig, ax))


def _fn_tex(s: str) -> str:
    """sin(x) -> \\sin(x) para que mathtext escriba las funciones en redonda."""
    s = re.sub(r"\batan\b", r"\\arctan", s)
    return re.sub(r"\b(sinh|cosh|tanh|sin|cos|tan|exp|log|ln|sec|csc|cot)\b", r"\\\1", s)


# --------------------------------------------------------------------------- utilidades
@functools.lru_cache(maxsize=4096)
def _compiled(text: str, variables: tuple):
    return compile_expr(text, variables)


def _names(spec) -> list[str]:
    return [c["name"] for c in spec["consts"]]


def default_values(spec) -> dict:
    return {c["name"]: c["value"] for c in spec["consts"]}


def sweep_values(c: dict) -> np.ndarray:
    lo, hi, n = c["min"], c["max"], int(c.get("n", 13))
    if c.get("integer"):
        return np.arange(int(round(lo)), int(round(hi)) + 1, dtype=float)
    sp = c.get("spacing", "uniform")
    if sp == "geom" and lo > 0:
        return np.geomspace(lo, hi, n)
    if sp == "symlog":
        m = max(abs(lo), abs(hi))
        pos = np.geomspace(m * 1e-3, m, max(n // 2, 2))
        return np.sort(np.concatenate([-pos, pos]))
    return np.linspace(lo, hi, n)


def _env(spec, values):
    v = default_values(spec)
    v.update({k: float(x) for k, x in (values or {}).items()})
    return v


def _defs_env(spec, env, var_env):
    """Evalúa las variables auxiliares (``defs``) del spec en orden."""
    out = dict(env)
    out.update(var_env)
    names = list(var_env) + list(env) + [d[0] for d in spec.get("defs", [])]
    for dname, dtxt in spec.get("defs", []):
        out[dname] = _compiled(dtxt, tuple(names))(**out)
    return out


def _eval(spec, text, env, **var_env):
    """Evalúa ``text`` con constantes (env), variables (x, y, t...) y defs."""
    names = tuple(list(var_env) + list(env) + [d[0] for d in spec.get("defs", [])])
    full = _defs_env(spec, env, var_env)
    return _compiled(str(text), names)(**full)


def _split(x, y, window):
    """Parte una curva en trazos continuos: corta en NaN, fuera de ventana y en polos."""
    x0, x1, y0, y1 = window
    W, H = x1 - x0, y1 - y0
    x = np.asarray(x, float); y = np.asarray(y, float)
    with np.errstate(all="ignore"):
        bad = ~np.isfinite(x) | ~np.isfinite(y) | (np.abs(y - (y0 + y1) / 2) > 3 * H) | (np.abs(x - (x0 + x1) / 2) > 3 * W)
        jump = (np.abs(np.diff(x)) > 1.5 * W) | (np.abs(np.diff(y)) > 1.5 * H)
    cut = np.zeros(len(x), bool)
    cut[1:] |= jump
    out, start = [], None
    for i in range(len(x)):
        if bad[i]:
            if start is not None and i - start >= 2:
                out.append(np.column_stack([x[start:i], y[start:i]]))
            start = None
        else:
            if start is not None and cut[i]:
                if i - start >= 2:
                    out.append(np.column_stack([x[start:i], y[start:i]]))
                start = None
            if start is None:
                start = i
    if start is not None and len(x) - start >= 2:
        out.append(np.column_stack([x[start:], y[start:]]))
    return out


def _valid_mask(spec, env, xs):
    if not spec.get("valid"):
        return None
    return _eval(spec, spec["valid"], env, x=xs) >= 0


# --------------------------------------------------------------------------- trazado de curvas
def curve_lines(spec, curve, env, res=3000):
    """Polilíneas de una curva (``explicit`` | ``vline`` | ``param`` | ``level``) para un valor de las constantes."""
    window = spec["window"]
    x0, x1, y0, y1 = window
    kind = curve.get("kind", spec["kind"])
    lines = []
    if kind == "explicit":
        xs = np.linspace(x0, x1, res)
        exprs = curve["y"] if isinstance(curve["y"], list) else [curve["y"]]
        mask = _valid_mask(curve if curve.get("valid") else spec, env, xs) if (curve.get("valid") or spec.get("valid")) else None
        for e in exprs:
            ys = np.broadcast_to(np.asarray(_eval(spec, e, env, x=xs), float), xs.shape).copy()
            if mask is not None:
                ys[~mask] = np.nan
            lines += _split(xs, ys, window)
    elif kind == "vline":
        xv = float(_eval(spec, curve["x"], env, x=0.0))
        if np.isfinite(xv):
            lines.append(np.array([[xv, y0], [xv, y1]]))
    elif kind == "param":
        var = curve.get("var", spec.get("var"))
        for lo, hi in curve.get("t", spec.get("t")):
            t = np.linspace(lo, hi, res * 2)
            xs = np.broadcast_to(np.asarray(_eval(spec, curve.get("x", spec.get("x")), env, **{var: t}), float), t.shape)
            ys = np.broadcast_to(np.asarray(_eval(spec, curve.get("y", spec.get("y")), env, **{var: t}), float), t.shape)
            lines += _split(xs, ys, window)
    elif kind == "level":
        lines += level_lines(spec, curve["F"], env, [float(_eval(spec, curve["c"], env, x=0.0, y=0.0))], res=500)[0]
    else:
        raise ValueError(kind)
    return lines


def level_grid(spec, F, env, res=500, clip=None, levels_hint=1.0):
    x0, x1, y0, y1 = spec["window"]
    xs = np.linspace(x0, x1, res)
    ys = np.linspace(y0, y1, res)
    X, Y = np.meshgrid(xs, ys)
    Z = np.broadcast_to(np.asarray(_eval(spec, F, env, x=X, y=Y), float), X.shape)
    lim = clip if clip is not None else 1e8
    Z = np.ma.masked_where(~np.isfinite(Z) | (np.abs(Z) > lim), Z)
    return xs, ys, Z


def _drop_pole_vertices(spec, F, env, xs, ys, Z, level, ln):
    """Quita vértices del contorno que no son un cruce real de F=nivel (polos de F, p. ej. 1/x).

    En un cruce genuino F(q)≈nivel (error ≪ variación de F en la celda); junto a un polo
    la interpolación lineal falla y |F(q)-nivel| es del orden de la variación de la celda.
    """
    if len(ln) < 2:
        return [ln]
    Fq = np.broadcast_to(np.asarray(_eval(spec, F, env, x=ln[:, 0], y=ln[:, 1]), float), (len(ln),))
    i = np.clip(np.searchsorted(xs, ln[:, 0]) - 1, 0, len(xs) - 2)
    j = np.clip(np.searchsorted(ys, ln[:, 1]) - 1, 0, len(ys) - 2)
    Zf = Z.filled(np.nan)
    corners = np.stack([Zf[j, i], Zf[j, i + 1], Zf[j + 1, i], Zf[j + 1, i + 1]])
    with np.errstate(all="ignore"):
        dF = np.nanmax(corners, axis=0) - np.nanmin(corners, axis=0)
        ok = np.isfinite(Fq) & (np.abs(Fq - level) <= 0.2 * dF + 1e-9 * (1 + abs(level)))
    if ok.all():
        return [ln]
    out, start = [], None
    for k, good in enumerate(ok):
        if good and start is None:
            start = k
        if (not good) and start is not None:
            if k - start >= 2:
                out.append(ln[start:k])
            start = None
    if start is not None and len(ln) - start >= 2:
        out.append(ln[start:])
    return out


def level_lines(spec, F, env, levels, res=500, clip=None):
    """[[polilíneas del nivel 1], [nivel 2], ...] de F(x,y)=nivel."""
    hint = max([abs(l) for l in levels] + [1.0])
    xs, ys, Z = level_grid(spec, F, env, res=res, clip=clip, levels_hint=hint)
    gen = contour_generator(xs, ys, Z)
    out = []
    for lv in levels:
        parts = []
        for l in gen.lines(float(lv)):
            parts += _drop_pole_vertices(spec, F, env, xs, ys, Z, float(lv), np.asarray(l))
        out.append(parts)
    return out, (xs, ys, Z)


# --------------------------------------------------------------------------- dibujo
def _plot_lines(ax, lines, **kw):
    for ln in lines:
        ax.plot(ln[:, 0], ln[:, 1], **kw)


def _level_const(spec):
    for c in spec["consts"]:
        if c.get("role") == "level":
            return c
    return None


def _intersections(a, b, limit=400):
    """Puntos de corte entre dos conjuntos de polilíneas (para marcar la ortogonalidad)."""
    def segs(lines):
        s = []
        for ln in lines:
            step = max(1, len(ln) // limit)
            ln = ln[::step]
            if len(ln) > 1:
                s.append(np.stack([ln[:-1], ln[1:]], axis=1))
        return np.concatenate(s) if s else np.zeros((0, 2, 2))
    A, B = segs(a), segs(b)
    if len(A) == 0 or len(B) == 0:
        return np.zeros((0, 2))
    p, r = A[:, 0][:, None, :], (A[:, 1] - A[:, 0])[:, None, :]
    q, s = B[:, 0][None, :, :], (B[:, 1] - B[:, 0])[None, :, :]
    den = r[..., 0] * s[..., 1] - r[..., 1] * s[..., 0]
    qp = q - p
    with np.errstate(all="ignore"):
        t = (qp[..., 0] * s[..., 1] - qp[..., 1] * s[..., 0]) / den
        u = (qp[..., 0] * r[..., 1] - qp[..., 1] * r[..., 0]) / den
    ok = (np.abs(den) > 1e-14) & (t >= 0) & (t <= 1) & (u >= 0) & (u <= 1)
    i, j = np.nonzero(ok)
    pts = p[i, 0] + t[i, j][:, None] * r[i, 0]
    return pts


def plot_spec(spec: Mapping, values: Mapping | None = None, ax=None, theme: str = "light", family: bool = True,
              extras: bool = True, particular: bool = True, field: bool = False, title: bool | str = True,
              legend: bool = True, res: int = 500, figsize=(6.2, 4.6), show: bool = False):
    """Dibuja un spec del catálogo (o creado con ``plot_*``). Devuelve ``(fig, ax)``."""
    th = THEMES[theme]
    env = _env(spec, values)
    created = ax is None
    if created:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.figure
    x0, x1, y0, y1 = spec["window"]
    fig.patch.set_facecolor(th["bg"]); ax.set_facecolor(th["bg"])
    handles = {}

    def mk(label, **kw):
        if label not in handles:
            handles[label] = ax.plot([], [], label=label, **kw)[0]

    kind = spec["kind"]
    # ---- campo de direcciones
    if field and spec.get("slope"):
        gx, gy = np.meshgrid(np.linspace(x0, x1, 25), np.linspace(y0, y1, 19))
        m = np.broadcast_to(np.asarray(_eval(spec, spec["slope"], env, x=gx, y=gy), float), gx.shape)
        ok = np.isfinite(m)
        norm = np.sqrt(1 + np.where(ok, m, 0) ** 2)
        ax.quiver(gx[ok], gy[ok], (1 / norm)[ok], (np.where(ok, m, 0) / norm)[ok], color=th["field"], alpha=.55,
                  angles="xy", pivot="mid", width=0.0028, headwidth=0, headlength=0, headaxislength=0, zorder=1)

    # ---- familias
    def draw_level_family(F, lc, color, name, zorder, label_family, label_sel):
        levels = sweep_values(lc) if family else np.array([])
        sel = env[lc["name"]]
        allv = list(levels) + [sel]
        res_lines, _ = level_lines(spec, F, env, allv, res=res)
        for lv, ln in zip(allv[:-1], res_lines[:-1]):
            _plot_lines(ax, ln, color=color, lw=0.9, alpha=.42, zorder=zorder)
        if len(levels):
            mk(label_family, color=color, lw=.9, alpha=.6)
        sel_lines = res_lines[-1]
        _plot_lines(ax, sel_lines, color=th["bg"], lw=5.2, zorder=zorder + 1)
        _plot_lines(ax, sel_lines, color=color, lw=2.8, zorder=zorder + 2)
        mk(label_sel.format(v=sel), color=color, lw=2.8)
        return sel_lines

    if kind == "level":
        lc = _level_const(spec)
        draw_level_family(spec["F"], lc, th["family"], lc["name"], 3,
                          f"familia ({lc['name']} variable)", lc["name"] + "={v:g}")
    elif kind == "ortho":
        c1 = next(c for c in spec["consts"] if c["name"] == spec["main"]["level"])
        c2 = next(c for c in spec["consts"] if c["name"] == spec["ortho"]["level"])
        l1 = draw_level_family(spec["main"]["F"], c1, th["family"], c1["name"], 3,
                               "familia principal", f"principal ({c1['name']}=" + "{v:g})")
        l2 = draw_level_family(spec["ortho"]["F"], c2, th["ortho"], c2["name"], 3,
                               "familia ortogonal", f"ortogonal ({c2['name']}=" + "{v:g})")
        pts = _intersections(l1, l2)
        if len(pts):
            ax.scatter(pts[:, 0], pts[:, 1], s=34, color=th["fg"], zorder=9, label="cortes (ángulo de 90°)")
    else:
        base = dict(spec)
        if family:
            for c in spec["consts"]:
                if not c.get("sweep", True) or c.get("role") == "level":
                    continue
                for v in sweep_values(c):
                    e2 = dict(env); e2[c["name"]] = float(v)
                    _plot_lines(ax, curve_lines(spec, spec, e2), color=th["family"], lw=.9, alpha=.42, zorder=3)
            mk("familia (constantes variables)", color=th["family"], lw=.9, alpha=.6)
        sel_lines = curve_lines(spec, spec, env)
        _plot_lines(ax, sel_lines, color=th["bg"], lw=5.2, zorder=5)
        _plot_lines(ax, sel_lines, color=th["family"], lw=2.8, zorder=6)
        shown = ", ".join(f"{c['name']}={env[c['name']]:g}" for c in spec["consts"]
                          if c.get("sweep", True) and c.get("role") != "level")
        mk(f"curva elegida ({shown})", color=th["family"], lw=2.8)

    # ---- soluciones singulares / extras
    if extras:
        for ex in spec.get("extras", []):
            _plot_lines(ax, curve_lines(spec, ex, env, res=3000), color=th["extra"], lw=1.7, ls=(0, (5, 3)), zorder=4)
        labels = [e.get("label") for e in spec.get("extras", []) if e.get("label")]
        if labels:
            mk("singulares: " + " · ".join(labels), color=th["extra"], lw=1.7, ls=(0, (5, 3)))

    # ---- solución particular (PVI)
    part = spec.get("particular") if particular else None
    if part:
        if "values" in part:
            e2 = dict(env); e2.update(part["values"])
            if kind in ("level", "ortho"):
                lc = _level_const(spec)
                lines, _ = level_lines(spec, spec["F"], e2, [e2[lc["name"]]], res=res)
                lines = lines[0]
            else:
                lines = curve_lines(spec, spec, e2)
        else:
            lines = curve_lines(spec, part["curve"], env)
        _plot_lines(ax, lines, color=th["bg"], lw=6.2, zorder=7)
        _plot_lines(ax, lines, color=th["particular"], lw=3.2, zorder=8)
        if part.get("point"):
            px = float(_eval(spec, part["point"][0], env, x=0.0)); py = float(_eval(spec, part["point"][1], env, x=0.0))
            ax.scatter([px], [py], s=70, color=th["particular"], edgecolor=th["bg"], linewidth=1.5, zorder=10)
        mk("solución particular: " + part.get("label", ""), color=th["particular"], lw=3.2)

    # ---- ejes, rejilla, título
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
    if spec.get("aspect") == "equal":
        ax.set_aspect("equal", adjustable="box")
    ax.grid(True, color=th["grid"], lw=.7, zorder=0)
    ax.axhline(0, color=th["axis"], lw=.9, zorder=2); ax.axvline(0, color=th["axis"], lw=.9, zorder=2)
    for sp in ax.spines.values():
        sp.set_color(th["axis"])
    ax.tick_params(colors=th["muted"], labelsize=8)
    ax.set_xlabel("x", color=th["muted"]); ax.set_ylabel("y", color=th["muted"])
    if title:
        t = title if isinstance(title, str) else spec.get("tex")
        if t:
            try:
                ax.set_title(f"${_tex(t)}$" if not isinstance(title, str) else t, color=th["fg"], fontsize=11)
                fig.canvas.draw()
            except Exception:
                ax.set_title(spec.get("id", ""), color=th["fg"], fontsize=11)
    if legend and handles:
        leg = ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=1, fontsize=7.5, frameon=False)
        for t_ in leg.get_texts():
            t_.set_color(th["muted"])
    if created:
        fig.tight_layout()
    if show:
        plt.show()
    return _finish(fig, ax, created)


def plot_problem(id_: str, values: Mapping | None = None, **kw):
    """Dibuja un problema del catálogo por su id (``"h3-17"`` = Hoja 3, ejercicio 17)."""
    return plot_spec(catalog.get(id_), values, **kw)


def plot_sheet(n: int, cols: int = 4, scale: float = 3.4, **kw):
    """Todos los problemas de la Hoja ``n`` en una cuadrícula de miniaturas."""
    ids = catalog.sheet_ids(n)
    rows = math.ceil(len(ids) / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(cols * scale, rows * scale * .85))
    for a in np.atleast_1d(axes).ravel():
        a.axis("off")
    for a, id_ in zip(np.atleast_1d(axes).ravel(), ids):
        a.axis("on")
        plot_spec(catalog.get(id_), ax=a, legend=False, title=f"{id_}", **kw)
        a.set_xlabel(""); a.set_ylabel("")
    fig.suptitle(f"Hoja {n}", fontsize=14)
    fig.tight_layout()
    return _finish(fig, axes)


# --------------------------------------------------------------------------- constructores de spec
def _const(name, v, sweep=True, role=None, n=13, **kw):
    if isinstance(v, (int, float)):
        lo = hi = float(v); val = float(v); sweep = False
    elif len(v) == 2:
        lo, hi = map(float, v); val = (lo + hi) / 2
    else:
        lo, hi, val = map(float, v)
    d = catalog.K(name, lo, hi, val, n=n, sweep=sweep, role=role, step=(hi - lo) / 200 if hi > lo else 1)
    d.update(kw)
    return d


def _consts(consts: Mapping, sweep=True):
    return [_const(k, v, sweep=sweep) for k, v in consts.items()]


def make_spec(kind: str, window, consts: Iterable[dict], tex: str = "", **kw) -> dict:
    spec = dict(id=kw.pop("id", "custom"), sheet=0, num=0, kind=kind, tex=tex, window=list(window), consts=list(consts))
    spec.update(kw)
    return spec


_PLOT_OPTS = ("values", "ax", "theme", "family", "field", "title", "legend", "res", "figsize", "show", "particular_on", "extras_on")


def _split_kw(kw: dict):
    """Separa opciones de dibujo de constantes: cualquier otro kwarg (``a=(0,3,1)``) es una constante."""
    opts, consts = {}, {}
    for k, v in kw.items():
        if k in _PLOT_OPTS:
            opts[{"particular_on": "particular", "extras_on": "extras"}.get(k, k)] = v
        else:
            consts[k] = v
    return opts, consts


def plot_level(F: str, C=(-3, 3, 0.0), window=(-5, 5, -5, 5), params: Mapping | None = None, level_name: str = "C",
               tex: str = "", slope: str | None = None, extras=None, particular=None, n: int = 13, spacing="uniform", **kw):
    """Soluciones implícitas ``F(x,y)=C``.

    ``C=(mín, máx, valor)``: rango de la constante (curvas de nivel) y valor resaltado. Otras constantes de ``F``
    (p. ej. ``a=(0.2, 4, 2)``) se pasan como argumentos con nombre o en ``params``.
    """
    opts, more = _split_kw(kw)
    consts = [_const(level_name, C, role="level", n=n, spacing=spacing)] + \
             [_const(k, v, sweep=False) for k, v in {**(params or {}), **more}.items()]
    spec = make_spec("level", window, consts, tex or f"F(x,y)={level_name}", F=F, slope=slope,
                     extras=extras or [], particular=particular)
    return plot_spec(spec, **opts)


def plot_explicit(y, window=(-5, 5, -5, 5), consts: Mapping | None = None, tex: str = "", slope=None, extras=None,
                  particular=None, valid=None, **kw):
    """Soluciones explícitas ``y=f(x; constantes)``. Constantes como argumentos: ``C=(-3, 3, 1)``.

    ``y`` puede ser una lista (ramas ``["sqrt(...)", "-sqrt(...)"]``). ``valid="expr"`` dibuja solo donde expr >= 0.
    """
    opts, more = _split_kw(kw)
    spec = make_spec("explicit", window, _consts({**(consts or {}), **more}), tex or "y=" + (y if isinstance(y, str) else y[0]),
                     y=y, slope=slope, extras=extras or [], particular=particular, valid=valid)
    return plot_spec(spec, **opts)


def plot_param(x: str, y: str, var: str, t, window=(-5, 5, -5, 5), consts: Mapping | None = None, tex: str = "",
               extras=None, **kw):
    """Soluciones paramétricas ``x(var), y(var)`` (EDOs de Lagrange, Clairaut...). ``t=(a,b)`` o lista de intervalos."""
    opts, more = _split_kw(kw)
    intervals = [list(t)] if np.ndim(t) == 1 else [list(i) for i in t]
    spec = make_spec("param", window, _consts({**(consts or {}), **more}), tex or f"x({var}),\\ y({var})", x=x, y=y, var=var,
                     t=intervals, extras=extras or [])
    return plot_spec(spec, **opts)


def plot_orthogonal(F1: str, F2: str, window=(-5, 5, -5, 5), params: Mapping | None = None, a=(-3, 3, 1), C=(-3, 3, 1),
                    tex: str = "", **kw):
    """Familia principal ``F1(x,y)=a`` y sus trayectorias ortogonales ``F2(x,y)=C`` (se marcan los cortes a 90°)."""
    opts, more = _split_kw(kw)
    consts = [_const("a", a, role="level", n=9), _const("C", C, role="level", n=9)] + \
             [_const(k, v, sweep=False) for k, v in {**(params or {}), **more}.items()]
    spec = make_spec("ortho", window, consts, tex or "F_1=a \\perp F_2=C", main=dict(F=F1, level="a"),
                     ortho=dict(F=F2, level="C"), aspect="equal")
    return plot_spec(spec, **opts)


# --------------------------------------------------------------------------- partir solo de la EDO (numérico)
def integral_curves(slope=None, M=None, N=None, window=(-5, 5, -5, 5), n_seeds=15, seed_x=None, params=None, steps=900):
    """Integra numéricamente la EDO ``y'=slope(x,y)`` o ``M dx + N dy = 0`` desde ``n_seeds`` puntos.

    Devuelve una lista de polilíneas. Se integra en longitud de arco (RK4), de modo que también
    funcionan las tangentes verticales.
    """
    from scipy.integrate import solve_ivp
    params = params or {}
    x0, x1, y0, y1 = window
    names = ("x", "y", *params)
    if slope is not None:
        fM, fN = compile_expr(f"-({slope})", names), compile_expr("1", names)
    else:
        fM, fN = compile_expr(str(M), names), compile_expr(str(N), names)
    sx = x0 + 0.5 * (x1 - x0) if seed_x is None else seed_x
    seeds = [(sx, y) for y in np.linspace(y0, y1, n_seeds + 2)[1:-1]]

    def rhs(s, u, sgn):
        m = float(fM(x=u[0], y=u[1], **params)); nn = float(fN(x=u[0], y=u[1], **params))
        nrm = math.hypot(m, nn)
        if not np.isfinite(nrm) or nrm == 0:
            return [0.0, 0.0]
        return [sgn * nn / nrm, -sgn * m / nrm]

    def left(s, u, sgn): return min(u[0] - x0, x1 - u[0], u[1] - y0, y1 - u[1])
    left.terminal = True; left.direction = -1
    L = 2.5 * math.hypot(x1 - x0, y1 - y0)
    lines = []
    for (px, py) in seeds:
        pieces = []
        for sgn in (1, -1):
            sol = solve_ivp(rhs, (0, L), [px, py], args=(sgn,), events=left, max_step=L / steps, rtol=1e-8, atol=1e-10)
            pieces.append(np.column_stack([sol.y[0], sol.y[1]]))
        # orientar: izquierda -> derecha
        a, b = pieces
        lines.append(np.vstack([a[::-1], b[1:]]) if np.isfinite(a).all() else b)
    return lines


def plot_ode(slope=None, M=None, N=None, window=(-5, 5, -5, 5), params=None, highlight=None, n_seeds=15,
             field=True, theme="light", ax=None, title=None, figsize=(6.2, 4.6), show=False):
    """Parte solo de la EDO (sin solución cerrada): campo de direcciones + curvas integrales numéricas.

    ``slope="sin(x-y)"`` para ``y'=sin(x-y)``; o ``M="..", N=".."`` para ``M dx + N dy = 0``.
    ``highlight=(x0, y0)`` resalta la curva integral por ese punto.
    """
    th = THEMES[theme]
    created = ax is None
    fig, ax = plt.subplots(figsize=figsize) if created else (ax.figure, ax)
    fig.patch.set_facecolor(th["bg"]); ax.set_facecolor(th["bg"])
    x0, x1, y0, y1 = window
    params = params or {}
    if field:
        gx, gy = np.meshgrid(np.linspace(x0, x1, 25), np.linspace(y0, y1, 19))
        if slope is not None:
            m = np.broadcast_to(np.asarray(compile_expr(slope, ("x", "y", *params))(x=gx, y=gy, **params), float), gx.shape)
        else:
            with np.errstate(all="ignore"):
                m = -np.asarray(compile_expr(str(M), ("x", "y", *params))(x=gx, y=gy, **params), float) / \
                    np.asarray(compile_expr(str(N), ("x", "y", *params))(x=gx, y=gy, **params), float)
        ok = np.isfinite(m)
        nr = np.sqrt(1 + np.where(ok, m, 0) ** 2)
        ax.quiver(gx[ok], gy[ok], (1 / nr)[ok], (np.where(ok, m, 0) / nr)[ok], color=th["field"], alpha=.55, angles="xy",
                  pivot="mid", width=.0028, headwidth=0, headlength=0, headaxislength=0, zorder=1)
    for ln in integral_curves(slope, M, N, window, n_seeds, params=params):
        ax.plot(ln[:, 0], ln[:, 1], color=th["family"], lw=.9, alpha=.5, zorder=3)
    if highlight is not None:
        # curva por el punto: se integra con una semilla propia
        lines = _curve_through(slope, M, N, window, highlight, params)
        for ln in lines:
            ax.plot(ln[:, 0], ln[:, 1], color=th["bg"], lw=5, zorder=5)
            ax.plot(ln[:, 0], ln[:, 1], color=th["family"], lw=2.8, zorder=6)
        ax.scatter([highlight[0]], [highlight[1]], s=60, color=th["family"], edgecolor=th["bg"], zorder=7)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
    ax.grid(True, color=th["grid"], lw=.7, zorder=0)
    ax.axhline(0, color=th["axis"], lw=.9); ax.axvline(0, color=th["axis"], lw=.9)
    ax.tick_params(colors=th["muted"], labelsize=8)
    ax.set_xlabel("x", color=th["muted"]); ax.set_ylabel("y", color=th["muted"])
    ax.set_title(title or (f"$y' = {_fn_tex(_tex(slope))}$" if slope else "$M\\,dx+N\\,dy=0$"), color=th["fg"], fontsize=11)
    if created:
        fig.tight_layout()
    if show:
        plt.show()
    return _finish(fig, ax, created)


def _curve_through(slope, M, N, window, pt, params):
    from scipy.integrate import solve_ivp
    names = ("x", "y", *params)
    if slope is not None:
        fM, fN = compile_expr(f"-({slope})", names), compile_expr("1", names)
    else:
        fM, fN = compile_expr(str(M), names), compile_expr(str(N), names)
    x0, x1, y0, y1 = window

    def rhs(s, u, sgn):
        m = float(fM(x=u[0], y=u[1], **params)); nn = float(fN(x=u[0], y=u[1], **params))
        nrm = math.hypot(m, nn)
        return [0.0, 0.0] if (not np.isfinite(nrm) or nrm == 0) else [sgn * nn / nrm, -sgn * m / nrm]

    def left(s, u, sgn): return min(u[0] - x0, x1 - u[0], u[1] - y0, y1 - u[1])
    left.terminal = True; left.direction = -1
    L = 2.5 * math.hypot(x1 - x0, y1 - y0)
    out = []
    for sgn in (1, -1):
        sol = solve_ivp(rhs, (0, L), list(pt), args=(sgn,), events=left, max_step=L / 900, rtol=1e-8, atol=1e-10)
        out.append(np.column_stack([sol.y[0], sol.y[1]]))
    return [np.vstack([out[1][::-1], out[0][1:]])]
