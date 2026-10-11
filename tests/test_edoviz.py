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
    from edoviz.plotting import ode_order
    spec = catalog.get(id_)
    gx, gy, m = field_vectors(spec, default_values(spec))
    if ode_order(spec) >= 2:       # 2.º orden: diagrama de fases; órdenes superiores: nada
        assert len(gx) == 0
    else:
        assert len(gx) > 5 and len(gx) == len(m)


PHASE_IDS = [i for i in IDS if catalog.get(i)["kind"] == "explicit" and "y2" in (catalog.get(i).get("ode") or "")
             and "y3" not in catalog.get(i).get("ode")]


def test_phase_portrait_coverage():
    from edoviz import has_phase_portrait, ode_order
    assert len(PHASE_IDS) >= 60
    assert all(has_phase_portrait(catalog.get(i)) for i in PHASE_IDS)
    assert [i for i in IDS if ode_order(catalog.get(i)) >= 3] == ["h3-15", "h3-16"]


@pytest.mark.parametrize("id_", PHASE_IDS)
def test_phase_portrait_renders(id_):
    from edoviz import plot_phase
    fig, ax = plot_phase(catalog.get(id_))
    assert len(ax.lines) > 3
    x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim()
    assert x1 > x0 and y1 > y0
    fig2, ax2 = plot_problem(id_, phase=True)
    assert ax2.get_xlabel() == "y" and ax2.get_ylabel() == "y′"
    fig3, ax3 = plot_problem(id_, field=True, yp=1.0)   # 2.º orden: campo de arcos en el plano (x, y)
    assert ax3.get_xlabel() == "x" and len(ax3.collections) >= 1
    plt.close(fig); plt.close(fig2); plt.close(fig3)


@pytest.mark.parametrize("id_", PHASE_IDS)
def test_arc_field(id_):
    from edoviz.plotting import arc_field, default_values
    spec = catalog.get(id_)
    for p in (0.0, 1.5):
        segs = arc_field(spec, default_values(spec), p)
        assert len(segs) > 100


def test_arc_field_matches_solution():
    """En y''=y, un arco con y'=p en (x,y) tiene curvatura y: comprobación directa."""
    from edoviz.plotting import arc_field, default_values
    spec = catalog.get("h4-06")                      # y'' - y = 0
    seg = arc_field(spec, default_values(spec), 0.0)[0]
    c = len(seg) // 2
    y_mid, t = seg[c, 1], seg[-1, 0] - seg[c, 0]
    assert abs((seg[-1, 1] - y_mid) - y_mid * t * t / 2) < 1e-9


def test_higher_order_has_no_field():
    fig, ax = plot_problem("h3-15", field=True)
    assert ax.get_xlabel() == "x" and not ax.collections
    plt.close(fig)


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
    base = {"-".join(i.split("-")[:2]) for i in IDS}          # h4-11-a -> h4-11
    assert base <= ids, sorted(base - ids)
    assert all(i in base for i in ids if i[:2] in ("h1", "h2", "h3"))   # hojas 1-3: todos con gráfica
    # los problemas con incisos tienen una gráfica por inciso
    assert {"h4-11-a", "h4-11-n", "h4-12-f"} <= set(IDS)


def test_patch_latex_inserts_one_figure_per_part(tmp_path):
    from edoviz import patch_latex
    out = tmp_path / "x.tex"
    n = patch_latex(ROOT / "tex" / "Metodos_Matematicos_I.tex", out, figdir="figs")
    txt = out.read_text(encoding="utf-8")
    assert n == len(IDS) and txt.count("\\includegraphics") == len(IDS)
    for i in ("h4-11-a", "h4-16-h", "h4-17-f", "h3-17"):
        assert f"figs/{i}.pdf" in txt


def test_expression_language():
    f = compile_expr("-x^2+2^-x+ln(x)*sen(x)", ["x"])
    assert abs(float(f(x=2.0)) - (-4 + 0.25 + 0.6931471805599453 * 0.9092974268256817)) < 1e-12
    assert str(compile_expr("(-8)^(1/3)", [])()) == "nan"
    with pytest.raises(ExprError):
        compile_expr("2x", ["x"])
    with pytest.raises(ExprError):
        compile_expr("__import__('os')", [])
