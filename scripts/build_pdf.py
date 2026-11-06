#!/usr/bin/env python3
"""Compila tex/main.tex y deja el PDF en docs/main.pdf (la vista previa de la página de inicio).

    python scripts/build_pdf.py

Hay que volver a ejecutarlo (y subir docs/main.pdf) cada vez que cambies tex/main.tex.
Necesita ``pdflatex``. Si el sistema no tiene el paquete de babel en español, se compila con babel en inglés
(solo cambian los guiones de palabra) y se escribe la fecha en español a mano.
"""
import datetime
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MESES = "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split()


def main():
    src = (ROOT / "tex" / "main.tex").read_text(encoding="utf-8")
    has_es = subprocess.run(["kpsewhich", "spanish.ldf"], capture_output=True, text=True).stdout.strip() != ""
    if not has_es:
        hoy = datetime.date.today()
        src = src.replace("[spanish]{babel}", "[english]{babel}")
        src = src.replace("\\begin{document}", f"\\date{{{hoy.day} de {MESES[hoy.month - 1]} de {hoy.year}}}\n\\begin{{document}}", 1)
        print("Aviso: sin babel español en este sistema; se usa babel inglés con la fecha escrita a mano.")
    with tempfile.TemporaryDirectory() as td:
        tex = Path(td) / "main.tex"
        tex.write_text(src, encoding="utf-8")
        for _ in range(2):
            r = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"], cwd=td, capture_output=True, text=True)
            if r.returncode:
                print(r.stdout[-2000:])
                sys.exit("pdflatex falló")
        out = ROOT / "docs" / "main.pdf"
        shutil.copy(Path(td) / "main.pdf", out)
    pages = re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", str(out)], capture_output=True, text=True).stdout)
    print(f"docs/main.pdf  ({out.stat().st_size // 1024} KB, {pages.group(1) if pages else '?'} páginas)")


if __name__ == "__main__":
    main()
