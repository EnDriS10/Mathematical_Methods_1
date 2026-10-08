"""Convierte el .tex de resoluciones (secciones «Hoja N», ejercicios «\\noindent\\textbf{N. ...}») a HTML.

El HTML conserva las fórmulas como ``\\( ... \\)`` / ``\\[ ... \\]`` para que las dibuje KaTeX en el navegador.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

TRIANGLE_SVG = (
    '<svg class="tri" viewBox="0 0 150 90" width="150" height="90" role="img" aria-label="triángulo con ángulo z">'
    '<polygon points="10,75 130,75 130,15" fill="none" stroke="currentColor" stroke-width="1.6"/>'
    '<path d="M32,75 A22,22 0 0 0 30.5,68" fill="none" stroke="currentColor"/>'
    '<text x="38" y="71" font-size="11" fill="currentColor" font-style="italic">z</text>'
    '<polyline points="124,75 124,69 130,69" fill="none" stroke="currentColor"/>'
    '<text x="55" y="88" font-size="10" fill="currentColor">1−u²</text>'
    '<text x="134" y="48" font-size="10" fill="currentColor">2u</text>'
    '<text x="42" y="38" font-size="10" fill="currentColor" transform="rotate(-7 42 38)">1+u²</text></svg>')


def _match_brace(s: str, i: int) -> int:
    """Índice de la llave que cierra la abierta en s[i] (== '{')."""
    depth = 0
    k = i
    while k < len(s):
        c = s[k]
        if c == "\\":
            k += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return k
        k += 1
    raise ValueError("llaves sin cerrar")


def _replace_cmd(s: str, cmd: str, fn) -> str:
    """Sustituye ``\\cmd{...}`` (con llaves anidadas) por ``fn(contenido)``."""
    out, i, tag = [], 0, "\\" + cmd + "{"
    while True:
        j = s.find(tag, i)
        if j < 0:
            out.append(s[i:])
            return "".join(out)
        out.append(s[i:j])
        k = _match_brace(s, j + len(tag) - 1)
        out.append(fn(s[j + len(tag):k]))
        i = k + 1


def _protect_math(s: str):
    """Saca las fórmulas a marcadores para tratar el texto sin tocarlas."""
    store = []

    def keep(m, display):
        body = m.group(1)
        body = body.replace("\\bm", "\\boldsymbol")
        store.append((display, html.escape(body, quote=False)))
        return f"\x00M{len(store) - 1}\x00"

    s = re.sub(r"\\begin\{align\*\}(.*?)\\end\{align\*\}", lambda m: keep(
        type("M", (), {"group": lambda self, n, b=m.group(1): "\\begin{aligned}" + b + "\\end{aligned}"})(), True), s, flags=re.S)
    s = re.sub(r"\\\[(.*?)\\\]", lambda m: keep(m, True), s, flags=re.S)
    s = re.sub(r"\$(.+?)\$", lambda m: keep(m, False), s, flags=re.S)
    return s, store


def _restore_math(s: str, store) -> str:
    def back(m):
        display, body = store[int(m.group(1))]
        return f"\\[{body}\\]" if display else f"\\({body}\\)"
    return re.sub(r"\x00M(\d+)\x00", back, s)


def to_html(src: str) -> str:
    s = re.sub(r"(?m)^\s*%.*$", "", src)                       # comentarios
    s = re.sub(r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}", "\x00TRI\x00", s, flags=re.S)
    s, store = _protect_math(s)
    s = re.sub(r"\\(?:noindent|separador|quad|qquad)\b", " ", s)
    s = re.sub(r"\\vspace\{[^}]*\}", "", s)
    s = s.replace("\\checkmark", "✓")
    for cmd, tag in (("textit", "em"), ("emph", "em"), ("textbf", "strong")):
        s = _replace_cmd(s, cmd, lambda c, t=tag: f"<{t}>{c}</{t}>")
    s = html.escape(s, quote=False).replace("&lt;em&gt;", "<em>").replace("&lt;/em&gt;", "</em>") \
        .replace("&lt;strong&gt;", "<strong>").replace("&lt;/strong&gt;", "</strong>")

    def itemize(m):
        items = [i.strip() for i in re.split(r"\\item\b", m.group(1)) if i.strip()]
        return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"

    inner = re.compile(r"\\begin\{itemize\}((?:(?!\\begin\{itemize\}).)*?)\\end\{itemize\}", re.S)
    while inner.search(s):                                              # listas anidadas: de dentro hacia fuera
        s = inner.sub(itemize, s)
    s = re.sub(r"\\\\(\[[^\]]*\])?", "<br>", s)
    s = re.sub(r"(?:\s*<br>\s*)+(?=\s*(?:\x00M\d+\x00\s*)?$)", "", s)   # <br> sobrantes al final
    s = s.replace("\x00TRI\x00", TRIANGLE_SVG)
    s = re.sub(r"^(?:\s*<br>\s*)+", "", s)                              # <br> sobrantes al inicio
    s = re.sub(r"\n\s*\n+", "\n", s).strip()
    return _restore_math(s, store)


SECTION = re.compile(r"\\section\{([^}]*)\}")
HEAD = re.compile(r"\\noindent\\textbf\{")


def parse_tex(path) -> dict:
    """Devuelve {title, author, course, sheets: [{n, title, problems: [{num, id, statement, solution}]}]}."""
    src = Path(path).read_text(encoding="utf-8")
    meta = dict(
        course=(re.search(r"\\large\s*([^}]+)\}", src) or [None, "Métodos Matemáticos I"])[1].strip(),
        author=re.sub(r"\\textbf\{|\}", "", (re.search(r"\\author\{(.*)\}", src) or [None, ""])[1]).strip(),
    )
    body = src[src.index("\\begin{document}"):src.index("\\end{document}")]
    parts = SECTION.split(body)          # [pre, título1, texto1, título2, texto2...]
    sheets = []
    for title, text in zip(parts[1::2], parts[2::2]):
        m = re.search(r"(\d+)", title)
        n = int(m.group(1)) if m else len(sheets) + 1
        problems = []
        heads = list(HEAD.finditer(text))
        for k, h in enumerate(heads):
            open_i = h.end() - 1
            close_i = _match_brace(text, open_i)
            head_txt = text[open_i + 1:close_i]
            end = heads[k + 1].start() if k + 1 < len(heads) else len(text)
            sol = text[close_i + 1:end]
            num_m = re.match(r"\s*(\d+)\.\s*(.*)", head_txt, re.S)
            num = int(num_m.group(1))
            problems.append(dict(
                num=num, id=f"h{n}-{num:02d}",
                statement=to_html(num_m.group(2)),
                solution=to_html(sol)))
        problems.sort(key=lambda p: p["num"])                          # el .tex puede traerlos desordenados
        sheets.append(dict(n=n, title=title.strip(), problems=problems))
    return dict(**meta, sheets=sheets)


if __name__ == "__main__":
    import json, sys
    d = parse_tex(sys.argv[1])
    print(json.dumps({s["title"]: len(s["problems"]) for s in d["sheets"]}, ensure_ascii=False))
