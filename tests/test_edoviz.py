import sys
from pathlib import Path

import matplotlib
import pytest

matplotlib.use("Agg")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib.pyplot as plt  # noqa: E402

from edoviz import catalog, check, plot_problem  # noqa: E402
from edoviz.expr import ExprError, compile_expr  # noqa: E402
from edoviz.texparse import parse_tex  # noqa: E402

IDS = list(catalog.SPECS)


@pytest.mark.parametrize("id_", IDS)
def test_solution_satisfies_its_ode(id_):
    """La solución del catálogo cumple su EDO (comprobación simbólica con sympy)."""
    count, worst, msgs = check.check_spec(catalog.get(id_))
    assert count >= 10, "muy pocos puntos válidos para comprobar"
    assert not msgs, msgs[:3]


@pytest.mark.parametrize("id_", IDS)
def test_plot_renders(id_):
    fig, ax = plot_problem(id_, field=True)
    assert len(ax.lines) > 0
    plt.close(fig)


def test_tex_matches_catalog():
    data = parse_tex(ROOT / "tex" / "Metodos_Matematicos_I.tex")
    ids = {p["id"] for s in data["sheets"] for p in s["problems"]}
    assert ids == set(IDS)


def test_expression_language():
    f = compile_expr("-x^2+2^-x+ln(x)*sen(x)", ["x"])
    assert abs(float(f(x=2.0)) - (-4 + 0.25 + 0.6931471805599453 * 0.9092974268256817)) < 1e-12
    assert str(compile_expr("(-8)^(1/3)", [])()) == "nan"
    with pytest.raises(ExprError):
        compile_expr("2x", ["x"])
    with pytest.raises(ExprError):
        compile_expr("__import__('os')", [])
