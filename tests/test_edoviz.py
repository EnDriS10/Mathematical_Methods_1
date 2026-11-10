import sys
import numpy as np
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
    data = parse_tex(ROOT / "tex" / "main.tex")
    ids = {p["id"] for s in data["sheets"] for p in s["problems"]}
    base = {"-".join(i.split("-")[:2]) for i in IDS}          # h4-11-a -> h4-11
    assert base <= ids, sorted(base - ids)
    assert all(i in base for i in ids if i[:2] in ("h1", "h2", "h3"))   # hojas 1-3: todos con gráfica
    # los problemas con incisos tienen una gráfica por inciso
    assert {"h4-11-a", "h4-11-n", "h4-12-f"} <= set(IDS)


def test_patch_latex_inserts_one_figure_per_part(tmp_path):
    from edoviz import patch_latex
    out = tmp_path / "x.tex"
    n = patch_latex(ROOT / "tex" / "main.tex", out, figdir="figs")
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


# ----------------------------------------------------------------------------- Hoja 5: series de potencias
H5 = [i for i in IDS if i.startswith("h5-")]


def test_hoja5_in_catalog_and_tex():
    data = parse_tex(ROOT / "tex" / "main.tex")
    h5 = next(s for s in data["sheets"] if s["n"] == 5)
    assert [p["num"] for p in h5["problems"]] == [1, 2, 3, 4, 5, 6, 7]
    assert H5 == ["h5-01-a", "h5-01-b", "h5-02", "h5-03", "h5-04", "h5-05", "h5-06", "h5-07"]


@pytest.mark.parametrize("id_", H5)
def test_series_satisfy_ode(id_):
    """Con N = 120 términos la suma parcial cumple la EDO (residuo ~ 0 en |x| < 0.7)."""
    from edoviz.plotting import _eval, default_values
    spec = catalog.get(id_)
    env = {**default_values(spec), "N": 120, "C1": 0.7, "C2": -0.4}
    x = np.array([-0.6, -0.2, 0.3, 0.65])
    h = 1e-3
    f = lambda xv: np.asarray(_eval(spec, spec["y"], env, x=xv), float)
    y, y1, y2 = f(x), (f(x + h) - f(x - h)) / (2 * h), (f(x + h) - 2 * f(x) + f(x - h)) / h ** 2
    res = _eval(spec, spec["ode"], env, x=x, y=y, y1=y1, y2=y2)
    assert np.abs(res).max() < 1e-3


def test_series_coefficients_match_hand_solution():
    from edoviz.expr import series_coeffs
    s1 = catalog.get("h5-01-a")["series"]                      # y'' + y' - x y = 0
    a = series_coeffs(s1[0], {})[:6]
    assert np.allclose(a, [1, 0, 0, 1 / 6, -1 / 24, 1 / 120])
    b = series_coeffs(s1[1], {})[:6]
    assert np.allclose(b, [0, 1, -1 / 2, 1 / 6, 1 / 24, -1 / 30])
    s7 = catalog.get("h5-07")["series"]                        # y'' + x² y = 1 + x + x²: yp = x²/2 + x³/6 + x⁴/12 ...
    yp = series_coeffs(s7[2], {})[:8]
    assert np.allclose(yp, [0, 0, 1 / 2, 1 / 6, 1 / 12, 0, -1 / 60, -1 / 252])


def test_n_slider_changes_curve_and_default_is_high():
    from edoviz.plotting import _eval, default_values
    spec = catalog.get("h5-06")
    n = next(c for c in spec["consts"] if c["name"] == "N")
    assert n["value"] >= 60 and n["max"] >= 100 and n.get("integer") and n.get("sweep") is False
    env = default_values(spec)
    x = np.array([2.5])
    y_hi = _eval(spec, spec["y"], env, x=x)
    y_lo = _eval(spec, spec["y"], {**env, "N": 3}, x=x)
    assert abs(y_hi - y_lo) > 1


def test_h5_hermite_polynomial_for_integer_p():
    from edoviz.plotting import _eval, default_values
    spec = catalog.get("h5-05")                                # p=3, a0=0, a1=1: y = x - 2x³/3 (polinomio de Hermite)
    env = default_values(spec)
    x = np.array([0.5, 1.7])
    assert np.allclose(_eval(spec, spec["y"], env, x=x), x - 2 * x ** 3 / 3)


def test_split_sheets(tmp_path):
    import importlib.util
    sp = importlib.util.spec_from_file_location("split_sheets", ROOT / "scripts" / "split_sheets.py")
    mod = importlib.util.module_from_spec(sp); sp.loader.exec_module(mod)
    files = mod.build(ROOT / "tex" / "main.tex", tmp_path)
    assert [f.name for f in files] == [f"Hoja_{n}.tex" for n in range(1, 7)]
    for f in files:
        t = f.read_text(encoding="utf-8")
        assert "separador" not in t
        assert "\\section{Hoja" not in t and "Versión interactiva" in t and "endris10.github.io/Mathematical_Methods_1" in t
        assert "únicamente para programar la página web" in t and "\\date{" in t
    assert "\\date{6 de noviembre de 2026}" in files[4].read_text(encoding="utf-8")
    assert sum(f.read_text(encoding="utf-8").count("\\includegraphics") for f in files) == len(IDS)


# ----------------------------------------------------------------------------- Hoja 6: series de Frobenius
H6 = [i for i in IDS if i.startswith("h6-")]


def test_hoja6_in_catalog_and_tex():
    data = parse_tex(ROOT / "tex" / "main.tex")
    h6 = next(s for s in data["sheets"] if s["n"] == 6)
    assert [p["num"] for p in h6["problems"]] == [1, 2, 3, 4, 5, 6, 7]
    assert H6 == ["h6-03-a", "h6-03-b", "h6-03-c", "h6-04", "h6-05-a", "h6-05-b", "h6-05-c", "h6-06", "h6-07"]
    # los incisos escritos como párrafos («\\noindent\\textbf{(a) ...}») se convierten en lista, como los de un itemize
    for num in (3, 5):
        sol = next(p for p in h6["problems"] if p["num"] == num)["solution"]
        assert sol.count("<li><strong>(") == 3


@pytest.mark.parametrize("id_", H6)
def test_frobenius_series_satisfy_ode(id_):
    """Las sumas parciales de Frobenius (|x|^m · serie) cumplen la EDO a ambos lados de x=0."""
    from edoviz.plotting import _eval, default_values
    spec = catalog.get(id_)
    env = {**default_values(spec), "N": 120, "C1": 0.7, "C2": -0.4}
    x = np.array([-0.6, -0.3, 0.3, 0.6])
    h = 1e-3
    f = lambda xv: np.asarray(_eval(spec, spec["y"], env, x=xv), float)
    y, y1, y2 = f(x), (f(x + h) - f(x - h)) / (2 * h), (f(x + h) - 2 * f(x) + f(x - h)) / h ** 2
    res = _eval(spec, spec["ode"], env, x=x, y=y, y1=y1, y2=y2)
    assert np.abs(res).max() < 1e-3 * max(1.0, np.abs(y2).max())


def test_frobenius_coefficients_match_hand_solution():
    from edoviz.expr import series_coeffs
    sp = lambda i, k: series_coeffs(catalog.get(i)["series"][k], {})
    assert np.allclose(sp("h6-03-b", 0)[:5], [1, -3, 2, -2 / 3, 1 / 7])
    assert np.allclose(sp("h6-03-b", 1)[:4], [1, -7 / 6, 21 / 40, -11 / 80])
    assert np.allclose(sp("h6-03-c", 0)[:5], [1, 1 / 5, 1 / 70, 1 / 1890, 1 / 83160])
    assert np.allclose(sp("h6-03-c", 1)[:5], [1, -1, -1 / 2, -1 / 18, -1 / 360])
    assert np.allclose(sp("h6-04", 0)[:6], [1, 1, 1 / 2, 1 / 6, 1 / 24, 1 / 120])        # a_n = 1/n!
    assert np.allclose(sp("h6-05-a", 0)[:6], [1, 1 / 2, 1 / 20, -1 / 60, -1 / 210, -1 / 3360])
    assert np.allclose(sp("h6-05-a", 1)[:7], [1, 1 / 2, 1 / 2, 0, -1 / 8, -3 / 80, -1 / 720])   # a_3 libre = 0
    assert np.allclose(sp("h6-05-b", 0)[[0, 4, 8, 12]], [1, -1 / 6, 1 / 120, -1 / 5040])     # sin(x²)
    assert np.allclose(sp("h6-05-b", 1)[[0, 4, 8, 12]], [1, -1 / 2, 1 / 24, -1 / 720])       # cos(x²)
    assert np.allclose(sp("h6-06", 0)[:7], [1, 0, -1 / 8, 0, 1 / 192, 0, -1 / 9216])


def test_cauchy_sum_series_problem7():
    """Hoja 6, problema 7: la recurrencia con suma de Cauchy reproduce a1, a2, a3 del .tex."""
    from edoviz.expr import series_coeffs
    k, A, al, E = 0.7, 1.3, 0.4, -0.5
    a = series_coeffs(catalog.get("h6-07")["series"][0], dict(k=k, A=A, alpha=al, E=E))
    assert np.allclose(a[1], k * A / 2)
    assert np.allclose(a[2], k * (k * A ** 2 - 2 * al * A - 2 * E) / 12)
    assert np.allclose(a[3], k * A * (k ** 2 * A ** 2 - 8 * al * k * A - 8 * k * E + 6 * al ** 2) / 144)


def test_patch_latex_puts_figures_under_paragraph_incisos(tmp_path):
    from edoviz import patch_latex
    out = tmp_path / "t.tex"
    patch_latex(ROOT / "tex" / "main.tex", out)
    t = out.read_text(encoding="utf-8")
    pos = [t.index("figs/" + i + ".pdf") for i in ("h6-03-a", "h6-03-b", "h6-03-c")]
    heads = [t.index(h) for h in (r"\textbf{(a) $\bm{2xy''+(3-x)y'-y=0}$", r"\textbf{(b) $\bm{2xy''+(x+1)y'+3y=0}$", r"\textbf{(c) $\bm{2x^2y''+xy'-(x+1)y=0}$")]
    assert heads[0] < pos[0] < heads[1] < pos[1] < heads[2] < pos[2]


def test_main_tex_has_no_web_note_and_repo_tex_folder():
    main = (ROOT / "tex" / "main.tex").read_text(encoding="utf-8")
    assert "Versión interactiva" not in main and "includegraphics" not in main and "\\newcommand{\\separador}" in main
    assert sorted(p.name for p in (ROOT / "tex").iterdir()) == ["Hoja_1.tex", "Hoja_2.tex", "Hoja_3.tex", "Hoja_4.tex", "Hoja_5.tex", "Hoja_6.tex", "main.tex"]
    assert (ROOT / "docs" / "main.pdf").stat().st_size > 50_000
