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


ANALYTIC = [i for i in IDS if catalog.get(i).get("analytic") or catalog.get(i).get("main", {}).get("analytic")]


@pytest.mark.parametrize("id_", ANALYTIC)
def test_analytic_form_satisfies_F(id_):
    """La forma despejada (analítica) cumple F(x,y)=nivel."""
    count, worst, msgs = check.check_analytic(catalog.get(id_))
    assert count > 20 and not msgs, msgs[:3]


@pytest.mark.parametrize("id_", ANALYTIC)
def test_numeric_method_still_works(id_):
    fig, ax = plot_problem(id_, method="numeric")
    assert len(ax.lines) > 0
    plt.close(fig)


@pytest.mark.parametrize("id_", IDS)
def test_every_problem_has_direction_field(id_):
    from edoviz.plotting import default_values, field_vectors
    spec = catalog.get(id_)
    gx, gy, m = field_vectors(spec, default_values(spec))
    assert len(gx) > 10 and len(gx) == len(m)


def test_selected_off_and_analytic_api():
    from edoviz import plot_analytic, plot_orthogonal_analytic
    fig, ax = plot_problem("h1-01", field=True, selected=False)
    assert all(l.get_linewidth() < 2 for l in ax.lines if len(l.get_xdata()) > 2)
    plt.close(fig)
    fig, ax = plot_analytic("tan(C-atan(x))", C=(-3, 3, 0.8))
    assert len(ax.lines) > 5
    plt.close(fig)
    fig, ax = plot_orthogonal_analytic("a*x^2", dict(x="sqrt(C)*cos(t)", y="sqrt(C/2)*sin(t)", var="t", t=(0, 6.2832)))
    assert len(ax.lines) > 5
    plt.close(fig)


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
