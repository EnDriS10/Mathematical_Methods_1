#!/usr/bin/env python3
"""Genera los datos de la web (docs/data/*.json) a partir del .tex y del catálogo de Python.

    python scripts/build_site.py

Ejecútalo cada vez que cambies el .tex (p. ej. al terminar la Hoja 4) o ``edoviz/catalog.py``.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from edoviz import catalog  # noqa: E402
from edoviz.texparse import parse_tex  # noqa: E402


def main():
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    data = ROOT / "docs" / "data"
    data.mkdir(parents=True, exist_ok=True)

    tex = parse_tex(ROOT / cfg["tex"])
    sheets = dict(site=dict(name=cfg["name"], course=cfg["course"]), sheets=tex["sheets"])
    (data / "sheets.json").write_text(json.dumps(sheets, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    (data / "catalog.json").write_text(json.dumps(catalog.SPECS, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    missing = [p["id"] for s in tex["sheets"] for p in s["problems"] if p["id"] not in catalog.SPECS]
    extra = [i for i in catalog.SPECS if i not in {p["id"] for s in tex["sheets"] for p in s["problems"]}]
    print(f"docs/data/sheets.json:  {sum(len(s['problems']) for s in tex['sheets'])} ejercicios en {len(tex['sheets'])} hojas")
    print(f"docs/data/catalog.json: {len(catalog.SPECS)} gráficas")
    if missing:
        print("Aviso: ejercicios del .tex sin gráfica en el catálogo:", ", ".join(missing))
    if extra:
        print("Aviso: gráficas del catálogo sin ejercicio en el .tex:", ", ".join(extra))


if __name__ == "__main__":
    main()
