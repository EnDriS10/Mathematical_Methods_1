"""Exportar las gráficas para el informe en LaTeX (PDF vectorial o PNG).

    from edoviz import export_figures, patch_latex
    export_figures("figs", sheets=[1, 2, 3])                       # figs/h1-01.pdf ... h3-20.pdf
    patch_latex("tex/Metodos_Matematicos_I.tex", "tex/MM1_con_graficas.tex", figdir="figs")
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Mapping

import matplotlib

from . import catalog


def export_figures(outdir="figs", sheets: Iterable[int] | None = None, ids: Iterable[str] | None = None,
                   formats=("pdf",), dpi: int = 220, theme: str = "print", values: Mapping[str, Mapping] | None = None,
                   figsize=(6.0, 4.4), **plot_kw):
    """Guarda una figura por problema (o por inciso: ``h4-11-a.pdf``). ``sheets=None`` = todas las hojas del catálogo.

    ``values={"h3-17": {"a": 2}}`` fija constantes concretas por problema.
    """
    import matplotlib.pyplot as plt
    from .plotting import plot_spec

    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    if sheets is None:
        sheets = sorted({v["sheet"] for v in catalog.SPECS.values()})
    chosen = list(ids) if ids else [i for n in sheets for i in catalog.sheet_ids(n)]
    written = []
    backend = matplotlib.get_backend()
    matplotlib.use("Agg")
    try:
        for id_ in chosen:
            fig, _ = plot_spec(catalog.get(id_), (values or {}).get(id_), theme=theme, figsize=figsize, **plot_kw)
            for fmt in formats:
                path = out / f"{id_}.{fmt}"
                fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor=fig.get_facecolor())
                written.append(path)
            plt.close(fig)
    finally:
        try:
            matplotlib.use(backend)
        except Exception:
            pass
    return written


_PROBLEM = re.compile(r"\\noindent\\textbf\{(\d+)\.")
_ITEM = re.compile(r"\\begin\{itemize\}|\\end\{itemize\}|\\item\b")


def _figure(figdir, id_, width, ext):
    return f"\n\\begin{{center}}\n\\includegraphics[width={width}]{{{figdir}/{id_}.{ext}}}\n\\end{{center}}\n"


def _item_end(src, start, limit):
    """Fin del ``\\item`` que empieza en ``start`` (respeta listas anidadas)."""
    depth = 0
    for m in _ITEM.finditer(src, start + 5, limit):
        tok = m.group()
        if tok.startswith("\\begin"):
            depth += 1
        elif tok.startswith("\\end"):
            if depth == 0:
                return m.start()
            depth -= 1
        elif depth == 0:
            return m.start()
    return limit


def patch_latex(tex_in, tex_out, figdir="figs", width=r"0.8\linewidth", ext="pdf"):
    """Copia el .tex insertando ``\\includegraphics`` en cada ejercicio que tenga figura.

    * ejercicio con una figura (``h3-17.pdf``): al final del ejercicio;
    * ejercicio con incisos (``h4-11-a.pdf``...): cada figura justo debajo de su inciso ``\\item \\textbf{(a) ...}``
      (si no se encuentra el inciso, al final del ejercicio).

    No modifica el original. Añade ``\\usepackage{graphicx}`` si falta.
    """
    src = Path(tex_in).read_text(encoding="utf-8")
    if "graphicx" not in src:
        src = src.replace("\\usepackage{amsmath, amssymb, amsfonts}", "\\usepackage{amsmath, amssymb, amsfonts}\n\\usepackage{graphicx}", 1)

    # límites de cada ejercicio: hasta el siguiente \noindent\textbf{N. , \separador o \section / \end{document}
    boundaries = [m.start() for m in re.finditer(r"\\noindent\\textbf\{\d+\.|\\separador|\\section\{|\\end\{document\}", src)]
    sections = [(m.start(), int(re.search(r"\d+", m.group(1)).group())) for m in re.finditer(r"\\section\{([^}]*)\}", src)]
    inserts = []                                   # (posición, texto)
    count = 0
    for m in _PROBLEM.finditer(src):
        start = m.start()
        sheet = max((n for pos, n in sections if pos < start), default=None)
        nxt = min((b for b in boundaries if b > start), default=len(src))
        id_ = f"h{sheet}-{int(m.group(1)):02d}"
        if id_ in catalog.SPECS:
            inserts.append((nxt, _figure(figdir, id_, width, ext) + "\n"))
            count += 1
        for pid in (i for i in catalog.SPECS if i.startswith(id_ + "-")):
            letter = catalog.SPECS[pid].get("part", pid.split("-")[-1])
            im = re.compile(r"\\item\s*\\textbf\{\(" + re.escape(letter) + r"\)").search(src, start, nxt)
            pos = _item_end(src, im.start(), nxt) if im else nxt
            inserts.append((pos, _figure(figdir, pid, width, ext) + ("\n" if not im else "")))
            count += 1
    for pos, block in sorted(inserts, key=lambda t: -t[0]):
        src = src[:pos] + block + src[pos:]
    Path(tex_out).write_text(src, encoding="utf-8")
    return count
