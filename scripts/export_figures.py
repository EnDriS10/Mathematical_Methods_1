#!/usr/bin/env python3
"""Exporta las figuras de las hojas (PDF vectorial) y, opcionalmente, genera un .tex con ellas insertadas.

    python scripts/export_figures.py                       # figs/h1-01.pdf ... h5-07.pdf
    python scripts/export_figures.py --sheets 3 --png      # solo la hoja 3, también en PNG
    python scripts/export_figures.py --patch               # además regenera tex/Hoja_1.tex ... Hoja_5.tex con las figuras
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from edoviz import catalog, export_figures  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sheets", type=int, nargs="*", default=sorted({s["sheet"] for s in catalog.SPECS.values()}))
    ap.add_argument("--out", default=str(ROOT / "figs"))
    ap.add_argument("--png", action="store_true", help="guardar también PNG")
    ap.add_argument("--patch", action="store_true", help="regenerar tex/Hoja_N.tex (una hoja por archivo, con las figuras) desde tex/main.tex")
    a = ap.parse_args()
    fmts = ("pdf", "png") if a.png else ("pdf",)
    files = export_figures(a.out, sheets=a.sheets, formats=fmts)
    print(f"{len(files)} archivos en {a.out}")
    if a.patch:
        sys.path.insert(0, str(ROOT / "scripts"))
        from split_sheets import build
        build()


if __name__ == "__main__":
    main()
