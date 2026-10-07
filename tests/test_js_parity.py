"""El motor JS (web) y el de Python deben evaluar igual todas las expresiones del catálogo."""
import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from edoviz import catalog  # noqa: E402
from edoviz.plotting import _eval, default_values  # noqa: E402


def _frag_exprs(frags):
    out = []
    for f in frags or []:
        if f["kind"] == "explicit":
            out += [(e, ["x"], None) for e in (f["y"] if isinstance(f["y"], list) else [f["y"]])]
            if f.get("valid"):
                out.append((f["valid"], ["x"], None))
        else:
            out += [(f["x"], [f["var"]], f["t"]), (f["y"], [f["var"]], f["t"])]
    return out


def _exprs(spec):
    out = []
    kind = spec["kind"]
    if kind == "level":
        out.append((spec["F"], ["x", "y"]))
        out += _frag_exprs(spec.get("analytic"))
    elif kind == "ortho":
        out += [(spec["main"]["F"], ["x", "y"]), (spec["ortho"]["F"], ["x", "y"])]
        out += _frag_exprs(spec["main"].get("analytic")) + _frag_exprs(spec["ortho"].get("analytic"))
    elif kind == "explicit":
        out += [(e, ["x"]) for e in (spec["y"] if isinstance(spec["y"], list) else [spec["y"]])]
        if spec.get("valid"):
            out.append((spec["valid"], ["x"]))
    elif kind == "param":
        out += [(spec["x"], [spec["var"]]), (spec["y"], [spec["var"]])]
    if spec.get("slope"):
        out.append((spec["slope"], ["x", "y"]))
    for ex in spec.get("extras", []):
        if ex["kind"] == "explicit":
            out.append((ex["y"], ["x"]))
        elif ex["kind"] == "vline":
            out.append((ex["x"], ["x"]))
    return out


def build_cases():
    rng = random.Random(7)
    cases = []
    for id_, spec in catalog.SPECS.items():
        env = default_values(spec)
        cn = [c["name"] for c in spec["consts"]]
        K = [env[n] for n in cn]
        x0, x1, y0, y1 = spec["window"]
        for item in _exprs(spec):
            text, vars_ = item[0], item[1]
            trange = item[2] if len(item) > 2 and item[2] else spec.get("t")
            pts = []
            for _ in range(25):
                pt = []
                for v in vars_:
                    if v == "y":
                        pt.append(rng.uniform(y0, y1))
                    elif v == "x":
                        pt.append(rng.uniform(x0, x1))
                    else:
                        lo, hi = rng.choice(trange)
                        pt.append(rng.uniform(lo, hi))
                pts.append(pt)
            kw = {}
            for k, v in enumerate(vars_):
                kw[v] = np.array([p[k] for p in pts])
            vals = np.broadcast_to(np.asarray(_eval(spec, text, env, **kw), float), (len(pts),))
            cases.append(dict(id=id_, text=text, vars=vars_, constNames=cn, defs=spec.get("defs", []), K=K,
                              points=pts, expected=[float(v) if np.isfinite(v) else None for v in vals]))
    return cases


def test_js_matches_python():
    cases = build_cases()
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(cases, fh)
    r = subprocess.run(["node", str(ROOT / "tests" / "js_parity_runner.js"), fh.name], capture_output=True, text=True)
    print(r.stdout, r.stderr)
    assert r.returncode == 0, r.stdout


if __name__ == "__main__":
    test_js_matches_python()
    print("OK")
