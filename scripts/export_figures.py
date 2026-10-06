#!/usr/bin/env python3
"""Exporta las figuras de las hojas (PDF vectorial) y, opcionalmente, genera un .tex con ellas insertadas.

    python scripts/export_figures.py                       # figs/h1-01.pdf ... h3-20.pdf
    python scripts/export_figures.py --sheets 3 --png      # solo la hoja 3, también en PNG
    python scripts/export_figures.py --patch               # además crea tex/<nombre>_con_graficas.tex
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from edoviz import catalog, export_figures, patch_latex  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sheets", type=int, nargs="*", default=sorted({s["sheet"] for s in catalog.SPECS.values()}))
    ap.add_argument("--out", default=str(ROOT / "figs"))
    ap.add_argument("--png", action="store_true", help="guardar también PNG")
    ap.add_argument("--patch", action="store_true", help="crear una copia del .tex con las figuras incluidas")
    a = ap.parse_args()
    fmts = ("pdf", "png") if a.png else ("pdf",)
    files = export_figures(a.out, sheets=a.sheets, formats=fmts)
    print(f"{len(files)} archivos en {a.out}")
    if a.patch:
        cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
        tex_in = ROOT / cfg["tex"]
        tex_out = tex_in.with_name(tex_in.stem + "_con_graficas.tex")
        import os
        figdir = os.path.relpath(a.out, tex_out.parent).replace(os.sep, "/")   # relativo a donde está el .tex
        n = patch_latex(tex_in, tex_out, figdir=figdir)
        print(f"{tex_out}: {n} figuras insertadas")


if __name__ == "__main__":
    main()
