"""Sliders interactivos dentro de Jupyter (ipywidgets): mueves las constantes y se resalta la curva."""
from __future__ import annotations

import matplotlib.pyplot as plt

from . import catalog
from .plotting import has_phase_portrait, plot_spec


def interactive(spec_or_id, theme: str = "light", figsize=(6.4, 4.8)):
    """``interactive("h3-17")`` o ``interactive(spec)``. Muestra un slider por constante y casillas de opciones."""
    import ipywidgets as w
    from IPython.display import display

    spec = catalog.get(spec_or_id) if isinstance(spec_or_id, str) else spec_or_id
    controls = {}
    for c in spec["consts"]:
        kw = dict(min=c["min"], max=c["max"], value=c["value"], description=c.get("label", c["name"]),
                  continuous_update=False, layout=w.Layout(width="420px"))
        if c.get("integer"):
            controls[c["name"]] = w.IntSlider(step=1, **{**kw, "min": int(c["min"]), "max": int(c["max"]), "value": int(c["value"])})
        else:
            controls[c["name"]] = w.FloatSlider(step=c.get("step") or (c["max"] - c["min"]) / 200, readout_format=".3g", **kw)
    controls["_family"] = w.Checkbox(value=True, description="todas las curvas")
    if has_phase_portrait(spec):       # EDO de 2.º orden: campo de arcos (y' = p) y diagrama de fases (y, y')
        controls["_field"] = w.Checkbox(value=False, description="campo (y′ = p)")
        controls["_phase"] = w.Checkbox(value=False, description="diagrama de fases")
        controls["_yp"] = w.FloatSlider(min=-5, max=5, step=.1, value=0, description="p", continuous_update=False)
    elif spec.get("slope") or (spec.get("ode") and "y2" not in spec["ode"] and "y3" not in spec["ode"]):
        controls["_field"] = w.Checkbox(value=False, description="campo de direcciones")
    if spec.get("extras"):
        controls["_extras"] = w.Checkbox(value=True, description="soluciones singulares")

    def redraw(**vals):
        opts = dict(family=vals.pop("_family"), field=vals.pop("_field", False), extras=vals.pop("_extras", True))
        if "_phase" in vals:
            opts["phase"] = vals.pop("_phase"); opts["yp"] = vals.pop("_yp")
        fig, _ = plot_spec(spec, vals, theme=theme, figsize=figsize, **opts)
        plt.show()
        plt.close(fig)

    out = w.interactive_output(redraw, controls)
    ui = w.VBox([w.HBox([controls[k] for k in controls if k.startswith("_")])] + [controls[c["name"]] for c in spec["consts"]])
    display(ui, out)
