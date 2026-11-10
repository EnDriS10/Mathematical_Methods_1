"""Genera tex/Hoja_N.tex (una hoja por archivo, con sus gráficas) a partir de tex/main.tex.

    python scripts/split_sheets.py                    # lee tex/main.tex y escribe tex/Hoja_1.tex ... Hoja_5.tex

* Cada Hoja_N.tex es un documento completo y compilable: sin ``\\section{Hoja N}`` (solo hay una hoja por archivo),
  con la nota inicial (enlace a la web + aviso de uso de IA) y los ``\\includegraphics`` de ``figs/``.
* Busca las figuras en ``figs/`` (Overleaf: carpeta ``figs`` junto al .tex) o en ``../figs/`` (este repositorio).
* ``tex/main.tex`` (las resoluciones sin gráficas) no se modifica.
"""
from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from edoviz.export import patch_latex  # noqa: E402

URL = "https://endris10.github.io/Mathematical_Methods_1/"
# fecha de entrega de cada hoja (aparece bajo el título de su Hoja_N.tex; main.tex no lleva fecha)
DATES = {1: "10 de septiembre de 2026", 2: "28 de septiembre de 2026", 3: "8 de octubre de 2026",
         4: "22 de octubre de 2026", 5: "6 de noviembre de 2026"}
NOTE = r"""
\begin{center}
\fbox{\parbox{0.93\linewidth}{\small
\textbf{Versión interactiva.} Todos los problemas de esta hoja se pueden visualizar e interactuar con sus gráficas
(constantes con deslizadores, curva elegida, campos de direcciones, etc.) en la página web
(pestaña ``Hoja %(n)d''):\\[2pt]
\centerline{\url{%(url)s}}\vspace{2pt}
Se utilizó IA (Claude, de Anthropic) \textbf{únicamente para programar la página web};
la resolución de las ecuaciones diferenciales es propia.}}
\end{center}
"""


def build(tex_in=None, outdir=None, url=URL):
    """Escribe ``Hoja_N.tex`` en ``outdir`` (por defecto ``tex/``) a partir de ``tex_in`` (por defecto ``tex/main.tex``)."""
    tex_in = Path(tex_in or ROOT / "tex" / "main.tex")
    out = Path(outdir or ROOT / "tex")
    url = url if url.endswith("/") else url + "/"
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "full.tex"
        patch_latex(tex_in, tmp, figdir=".")
        src = tmp.read_text(encoding="utf-8").replace("{./", "{")
    head, rest = src.split(r"\begin{document}", 1)
    head = head.replace(r"\usepackage{bm}", "\\usepackage{bm}\n\\usepackage[hidelinks]{hyperref}\n\\graphicspath{{figs/}{../figs/}}", 1)
    rest = rest.replace(r"\end{document}", "")
    # las hojas individuales no llevan la línea discontinua entre hojas (solo main.tex): fuera \separador y su definición
    head = re.sub(r"(?m)^% Línea discontinua entre ejercicios\n\\newcommand\{\\separador\}.*\n?", "", head)
    rest = re.sub(r"(?m)^[ \t]*\\separador[ \t]*\n?", "", rest)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for p in re.split(r"(?=\\section\{Hoja \d+\})", rest):
        m = re.match(r"\\section\{Hoja (\d+)\}[ \t]*\n?", p)
        if not m or not re.search(r"\\noindent\s*(?:\\textbf\{|\{\\bfseries\s*)\d+\.", p):
            continue                                        # introducción u hoja sin ejercicios
        n = int(m.group(1))
        body = p[m.end():].strip()                          # sin \section{Hoja N}
        h = re.sub(r"(\\large Métodos Matemáticos I)", r"\1 --- Hoja %d" % n, head, count=1)
        date = "\\date{%s}\n" % DATES.get(n, "")      # sin fecha conocida: \date{} vacío (si no, LaTeX pone la de compilación)
        doc = (h + date + "\\begin{document}\n\n\\maketitle\n\\vspace{-0.2cm}\n" + NOTE % dict(url=url, n=n)
               + "\n" + body + "\n\n\\end{document}\n")
        path = out / f"Hoja_{n}.tex"
        path.write_text(doc, encoding="utf-8")
        written.append(path)
        print(f"Hoja {n} -> {path}  ({doc.count(chr(92) + 'includegraphics')} figuras)")
    return written


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tex_in", nargs="?", default=None)
    ap.add_argument("outdir", nargs="?", default=None)
    ap.add_argument("--url", default=URL)
    a = ap.parse_args()
    build(a.tex_in, a.outdir, a.url)


if __name__ == "__main__":
    main()
