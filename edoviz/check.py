"""Validación simbólica: ¿cada solución del catálogo cumple realmente su EDO?

Usa sympy para derivar la solución (explícita, implícita o paramétrica) y
comprueba, en puntos aleatorios de la ventana, que el residuo de la EDO es ~0.
Para las trayectorias ortogonales comprueba además que ∇F1·∇F2 = 0.

    python -m edoviz.check            # todo el catálogo
    python -m edoviz.check h3-17      # un problema
"""
from __future__ import annotations

import random
import sys

import numpy as np
import sympy as sp

from . import catalog
from .expr import ALIASES, CONSTS, FUNCS, ExprError, _Parser, _tokenize


def _cbrt(u):
    return sp.Piecewise((u ** sp.Rational(1, 3), u >= 0), (-((-u) ** sp.Rational(1, 3)), True))


def _sel(c, a, b):
    return sp.Piecewise((a, c > 0), (b, True))


_SP = {
    "sin": "sp.sin", "cos": "sp.cos", "tan": "sp.tan", "asin": "sp.asin", "acos": "sp.acos", "atan": "sp.atan",
    "atan2": "sp.atan2", "sinh": "sp.sinh", "cosh": "sp.cosh", "tanh": "sp.tanh", "asinh": "sp.asinh",
    "acosh": "sp.acosh", "atanh": "sp.atanh", "exp": "sp.exp", "log": "sp.log", "log10": "_log10",
    "log2": "_log2", "sqrt": "sp.sqrt", "cbrt": "_cbrt", "abs": "sp.Abs", "sign": "sp.sign",
    "floor": "sp.floor", "ceil": "sp.ceiling", "min": "sp.Min", "max": "sp.Max",
    "sec": "_sec", "csc": "_csc", "cot": "_cot", "sel": "_sel",
}
_NS = dict(sp=sp, _cbrt=_cbrt, _sel=_sel, _log10=lambda u: sp.log(u, 10), _log2=lambda u: sp.log(u, 2),
           _sec=lambda u: 1 / sp.cos(u), _csc=lambda u: 1 / sp.sin(u), _cot=lambda u: 1 / sp.tan(u))
_CONST_SP = {"pi": "sp.pi", "e": "sp.E", "nan": "sp.nan", "inf": "sp.oo"}


class _SymParser(_Parser):
    funcs = _SP
    consts = _CONST_SP

    def pow(self, base, exp):
        return f"(({base})**({exp}))"


def sym(text, names):
    """Expresión de texto -> expresión sympy (símbolos reales, cada nombre en ``names``)."""
    parser = _SymParser(_tokenize(str(text)), names)
    code = parser.expr()
    if parser.i != len(parser.t):
        raise ExprError(f"Sobran símbolos en {text!r}")
    ns = dict(_NS)
    for n in names:
        ns[f"v_{n}"] = sp.Symbol(n, real=True)
    return eval(code, ns)  # noqa: S307


def _num(e, **vals):
    try:
        v = complex(e.subs({sp.Symbol(k, real=True): val for k, val in vals.items()}).evalf())
    except Exception:
        return None
    if abs(v.imag) > 1e-9 or not np.isfinite(v.real):
        return None
    return v.real


def _scale(*vals):
    return 1.0 + sum(abs(v) for v in vals if v is not None)


def _const_samples(spec, rng):
    out = {}
    for c in spec["consts"]:
        v = rng.uniform(c["min"], c["max"])
        if c.get("integer"):
            v = round(v)
        out[c["name"]] = v
    return out


def _derivs(base_y, t, xt=None, order=3):
    """[y, y', y'', ...] como funciones de t (si xt es None, t es x)."""
    ds = [base_y]
    for _ in range(order):
        d = sp.diff(ds[-1], t)
        ds.append(d if xt is None else d / sp.diff(xt, t))
    return ds


def _residual_expr(ode, names):
    return sym(ode, names + ["y1", "y2", "y3"])


def check_spec(spec, n=40, seed=1, tol=1e-6):
    """Devuelve (n_comprobados, peor_error, mensajes)."""
    rng = random.Random(seed)
    msgs, worst, count = [], 0.0, 0
    cn = [c["name"] for c in spec["consts"]]
    x0, x1, y0, y1_ = spec["window"]
    kind = spec["kind"]
    odes = []
    if spec.get("ode"):
        odes.append(spec["ode"])
    if spec.get("slope"):
        odes.append(f"y1-({spec['slope']})")

    def run(sets, ders, resid):
        nonlocal worst, count
        # sets: iterable of dict(valores) ; ders: lambda(vals)->(x,y,y1,y2,y3) numericos o None
        for vals in sets:
            r = ders(vals)
            if r is None:
                continue
            x, y, d1, d2, d3 = r
            rv = _num(resid, x=x, y=y, y1=d1, y2=d2, y3=d3, **{k: v for k, v in vals.items() if k in cn})
            if rv is None:
                continue
            err = abs(rv) / _scale(x, y, d1, d2, d3)
            worst, count = max(worst, err), count + 1
            if err > tol:
                msgs.append(f"residuo {rv:.3g} (rel {err:.2g}) en {vals}")

    if kind in ("level", "ortho"):
        x, y = sp.symbols("x y", real=True)
        fams = [(spec["F"], spec.get("level"), odes)] if kind == "level" else \
               [(spec["main"]["F"], None, [spec["ode"]] if spec.get("ode") else []),
                (spec["ortho"]["F"], None, [spec["ode_ortho"]] if spec.get("ode_ortho") else [])]
        syms = {}
        for Ftxt, _, olist in fams:
            F = sym(Ftxt, ["x", "y"] + cn)
            Fx, Fy = sp.diff(F, x), sp.diff(F, y)
            p = -Fx / Fy
            p2 = sp.diff(p, x) + sp.diff(p, y) * p
            p3 = sp.diff(p2, x) + sp.diff(p2, y) * p
            syms[Ftxt] = (F, Fx, Fy)
            for ode in olist:
                resid = _residual_expr(ode, ["x", "y"] + cn).subs(
                    {sp.Symbol("y1", real=True): p, sp.Symbol("y2", real=True): p2, sp.Symbol("y3", real=True): p3})
                pts = []
                for _ in range(n * 3):
                    pts.append(dict(x=rng.uniform(x0, x1), y=rng.uniform(y0, y1_), **_const_samples(spec, rng)))
                def ders(v, resid=resid):
                    return (v["x"], v["y"], 0, 0, 0)
                run(pts, ders, resid)
        if kind == "ortho":
            (F1, F1x, F1y), (F2, F2x, F2y) = syms[spec["main"]["F"]], syms[spec["ortho"]["F"]]
            dot = F1x * F2x + F1y * F2y
            for _ in range(n * 3):
                v = dict(x=rng.uniform(x0, x1), y=rng.uniform(y0, y1_), **_const_samples(spec, rng))
                val = _num(dot, **v)
                if val is None:
                    continue
                g1 = _num(sp.sqrt(F1x ** 2 + F1y ** 2), **v)
                g2 = _num(sp.sqrt(F2x ** 2 + F2y ** 2), **v)
                if not g1 or not g2:
                    continue
                err = abs(val) / (g1 * g2)
                worst, count = max(worst, err), count + 1
                if err > tol:
                    msgs.append(f"∇F1·∇F2 = {val:.3g} (cos {err:.2g}) en {v}")
        return count, worst, msgs

    defs = spec.get("defs", [])
    if kind == "explicit":
        x = sp.Symbol("x", real=True)
        names = ["x"] + cn
        env = {}
        for dname, dtxt in defs:                      # expandir variables auxiliares
            env[sp.Symbol(dname, real=True)] = sym(dtxt, names + [d[0] for d in defs]).xreplace(env)
        valid = sym(spec["valid"], names).xreplace(env) if spec.get("valid") else None
        ys = spec["y"] if isinstance(spec["y"], list) else [spec["y"]]
        sets = [_const_samples(spec, rng) for _ in range(n * 3)] + list(
            {**_const_samples(spec, rng), **o} for o in spec.get("check_overrides", []) for _ in range(n))
        for ytxt in ys:
            ysym = sym(ytxt, names + [d[0] for d in defs]).xreplace(env)
            ds = _derivs(ysym, x)
            for ode in odes:
                resid = _residual_expr(ode, ["x", "y"] + cn).subs(
                    {sp.Symbol(k, real=True): v for k, v in zip(["y", "y1", "y2", "y3"], ds)})
                for cs in sets:
                    v = dict(x=rng.uniform(x0, x1), **cs)
                    if valid is not None:
                        vv = _num(valid, **v)
                        if vv is None or vv < 0:
                            continue
                    val = _num(resid, **v)
                    dv = [_num(d, **v) for d in ds]
                    if val is None or any(d is None for d in dv):
                        continue
                    err = abs(val) / _scale(*dv, v["x"])
                    worst, count = max(worst, err), count + 1
                    if err > tol:
                        msgs.append(f"residuo {val:.3g} (rel {err:.2g}) en {v}")
        return count, worst, msgs

    if kind == "param":
        t = sp.Symbol(spec["var"], real=True)
        names = [spec["var"]] + cn
        xs, ys = sym(spec["x"], names), sym(spec["y"], names)
        ds = _derivs(ys, t, xs)
        for ode in odes:
            resid = _residual_expr(ode, ["x", "y"] + cn)
            resid = resid.subs({sp.Symbol("x", real=True): xs, sp.Symbol("y", real=True): ys,
                                sp.Symbol("y1", real=True): ds[1], sp.Symbol("y2", real=True): ds[2],
                                sp.Symbol("y3", real=True): ds[3]})
            for _ in range(n * 4):
                lo, hi = rng.choice(spec["t"])
                v = {spec["var"]: rng.uniform(lo, hi), **_const_samples(spec, rng)}
                val = _num(resid, **v)
                dv = [_num(e, **v) for e in (xs, ys, ds[1])]
                if val is None or any(d is None for d in dv):
                    continue
                err = abs(val) / _scale(*dv)
                worst, count = max(worst, err), count + 1
                if err > tol:
                    msgs.append(f"residuo {val:.3g} (rel {err:.2g}) en {v}")
        return count, worst, msgs
    raise ValueError(kind)


def main(argv=None):
    ids = (argv or sys.argv[1:]) or list(catalog.SPECS)
    bad = 0
    for id_ in ids:
        spec = catalog.get(id_)
        try:
            count, worst, msgs = check_spec(spec)
        except Exception as exc:  # pragma: no cover
            print(f"{id_}: ERROR {type(exc).__name__}: {exc}")
            bad += 1
            continue
        status = "OK " if not msgs and count >= 10 else "FALLO"
        if status != "OK ":
            bad += 1
        print(f"{id_}: {status} {count:3d} comprobaciones, peor error relativo {worst:.1e}")
        for m in msgs[:3]:
            print("      ", m)
    print("\nTodos los problemas validados." if not bad else f"\n{bad} problema(s) con incidencias.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
