"""edoviz: gráficas de familias de soluciones de EDOs (Métodos Matemáticos I)."""
from .catalog import SPECS, get as get_spec, sheet_ids
from .expr import compile_expr
from .widgets import interactive
from .export import export_figures, patch_latex
from .plotting import (default_values, integral_curves, plot_explicit, plot_level, plot_ode, plot_orthogonal,
                       plot_param, plot_problem, plot_sheet, plot_spec, plot_analytic, plot_orthogonal_analytic,
                       as_fragments)

__all__ = ["interactive", "export_figures", "patch_latex", "SPECS", "get_spec", "sheet_ids", "compile_expr", "default_values", "integral_curves", "plot_explicit",
           "plot_level", "plot_ode", "plot_orthogonal", "plot_param", "plot_problem", "plot_sheet", "plot_spec",
           "plot_analytic", "plot_orthogonal_analytic", "as_fragments"]
