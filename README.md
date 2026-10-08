# Métodos Matemáticos I · Familias de soluciones de EDOs

**César Acosta** — resolución de las hojas de problemas de ecuaciones diferenciales ordinarias, con gráficas de
todas las curvas integrales, soluciones paramétricas y trayectorias ortogonales.

Este repositorio tiene tres piezas que comparten los mismos datos:

| Pieza | Para qué | Dónde |
|---|---|---|
| **Paquete Python `edoviz`** + **notebook** | Graficar con funciones (matplotlib) y exportar figuras al LaTeX | `edoviz/`, `notebooks/edo_graficas.ipynb` |
| **Web interactiva** (GitHub Pages) | Ver la resolución de cada hoja y mover las constantes con sliders | `docs/` |
| **LaTeX** | Tus resoluciones y el informe con las figuras insertadas | `tex/`, `figs/` |

Cada ejercicio está descrito **una sola vez** en `edoviz/catalog.py` (la solución como texto + el rango de sus constantes).
Python lo dibuja con matplotlib y la web lo dibuja en el navegador con el mismo texto (un test comprueba que ambos motores dan los mismos valores).

## Empezar

```bash
pip install -r requirements.txt
jupyter lab notebooks/edo_graficas.ipynb
```

```python
from edoviz import *

plot_problem("h3-17")                                   # ejercicio 17 de la Hoja 3 (familia y ortogonales)
plot_problem("h1-03", values={"K": 2}, field=True)      # otra constante + campo de direcciones
plot_sheet(1)                                           # toda la Hoja 1 en miniaturas

# tus propias soluciones: solo escribes la solución; cada constante es (mín, máx, valor_resaltado)
plot_level("atan(x)+atan(y)", C=(-3, 3, 0.8))                      # F(x,y) = C
plot_analytic("tan(C-atan(x))", C=(-3, 3, 0.8))                    # solución despejada (analítica, exacta)
plot_level("atan(x)+atan(y)", C=(-3, 3, 0.8), method="numeric")    # contornos de F (numérico)
plot_explicit("exp(-x)+C*exp(-2*x)", C=(-3, 3, 1))                 # y = f(x; C)
plot_param("(p+1)*exp(p)+C", "p^2*exp(p)", var="p", t=(-10, 2), C=(-4, 4, 0))   # x(p), y(p)
plot_orthogonal("y/x^n", "x^2+n*y^2", n=(0.5, 4, 2), a=(-3, 3, 1.5), C=(0.5, 12, 5.5))
plot_orthogonal_analytic("a*x^n", dict(x="sqrt(C)*cos(t)", y="sqrt(C/n)*sin(t)", var="t", t=(0, 6.2832)),
                         n=(0.5, 4, 2), a=(-3, 3, 1.5), C=(0.5, 12, 5.5))      # solo soluciones despejadas
plot_problem("h1-01", field=True, selected=False)       # campo de direcciones sin la curva elegida

# solo tienes la EDO (sin resolver): integración numérica + campo de direcciones
plot_ode(slope="sin(x-y)", highlight=(0, 1))

interactive("h3-17")                                    # sliders dentro de Jupyter
```

Las expresiones son texto: `+ - * / ^`, `sin cos tan asin acos atan sinh cosh tanh exp log(=ln) sqrt cbrt abs sign min max`,
constantes `pi` y `e`. No hay multiplicación implícita (`2*x`, no `2x`).

## Figuras para el LaTeX

```bash
python scripts/export_figures.py --patch
```

Crea una figura por ejercicio, `figs/h1-01.pdf … h4-19.pdf` (PDF vectorial), y una **por inciso** cuando el ejercicio los tiene:
`figs/h4-11-a.pdf`, `h4-11-b.pdf`… (cada una se inserta justo debajo de su inciso en el `.tex`) y `tex/Metodos_Matematicos_I_con_graficas.tex`: una copia de tu `.tex`
con cada figura al final de su ejercicio (`\includegraphics{../figs/...}`; tu `.tex` original no se modifica).
Opciones: `--sheets 3`, `--png`. Desde Python: `export_figures(...)`, `patch_latex(...)`; constantes concretas por
ejercicio con `values={"h3-17": {"a": 2, "C": 8}}`.

## La web

Abre `docs/index.html` a través de un servidor local (el navegador no deja leer los JSON desde `file://`):

```bash
python scripts/build_site.py          # regenera docs/data/*.json desde el .tex y el catálogo
python -m http.server -d docs 8000    # http://localhost:8000
```

En cada ejercicio: **sliders** por constante (la curva elegida se resalta en trazo grueso sobre la familia completa),
**clic** en el gráfico para elegir la curva que pasa por ese punto, **rueda** para ampliar, **arrastrar** para mover,
campo de direcciones, soluciones singulares/particulares y **Descargar PNG**. Enlaces directos: `#hoja-3/17`.

### Publicarla en GitHub Pages

```bash
git init -b main
git add .
git commit -m "Métodos Matemáticos I: EDOs"
git remote add origin https://github.com/<tu-usuario>/<repositorio>.git
git push -u origin main
```

Después, en GitHub: **Settings → Pages → Build and deployment → Source: Deploy from a branch → Branch: `main`, carpeta `/docs`**.
La web quedará en `https://<tu-usuario>.github.io/<repositorio>/`. No hay que compilar nada: KaTeX (las fórmulas) va incluido en `docs/vendor/`.

## Añadir la Hoja 5 (o cualquier ejercicio nuevo)

1. Escribe la resolución en `tex/Metodos_Matematicos_I.tex` bajo `\section{Hoja 5}`, con el mismo formato (`\noindent\textbf{1. ...}`).
2. Añade una entrada por ejercicio en `edoviz/catalog.py`. Copia una parecida; los tipos son `level` (implícita),
   `explicit`, `param` y `ortho`:
   ```python
   level("h5-01", "x^2*y", K("C", -5, 5, 1), [-4, 4, -4, 4], r"x^2y=C", slope="-2*y/x")
   explicit("h5-02", "C*exp(2*x)", [K("C", -3, 3, 1)], [-2, 2, -6, 6], r"y=Ce^{2x}", slope="2*y")
   ```
3. Comprueba que la solución cumple la EDO: `python -m edoviz.check h5-01`
   (derivación simbólica con sympy; si no das `slope`, pasa `ode="..."` con `y1,y2,y3` = derivadas, igualada a 0).
   Si el ejercicio tiene incisos, una entrada por inciso con el sufijo de la letra (`h4-11-a`, `h4-11-b`…): la web los muestra con un
   selector y las figuras se llaman igual. Los ejercicios teóricos (sin gráfica) no necesitan entrada.
4. Añade una descripción breve de la hoja en `config.json` (`"descriptions": {"5": "..."}`); aparece en la tarjeta de inicio y al abrir la hoja.
5. `python scripts/build_site.py`, y de nuevo `git add . && git commit && git push`.

Campos útiles del catálogo: `extras=[...]` (soluciones singulares, discontinuas), `particular=...` (condición inicial, en verde),
`slope="..."` (campo de direcciones), `valid="expr"` (dibuja solo donde expr ≥ 0), `aspect="equal"`.

## Comprobaciones

```bash
pytest -q
```

Más de 400 tests: cada una de las soluciones del catálogo **cumple su EDO** (derivación simbólica y evaluación en puntos aleatorios),
todas las gráficas se dibujan, el parser de tu `.tex` encuentra los mismos ejercicios que el catálogo y el motor de expresiones de la web (JS)
coincide con el de Python.

## Estructura

```
edoviz/            paquete Python (expr, catalog, plotting, check, export, texparse, widgets)
notebooks/         edo_graficas.ipynb (generado por scripts/make_notebook.py)
scripts/           build_site.py · export_figures.py · make_notebook.py
docs/              la web (GitHub Pages): index.html, css/, js/, data/, vendor/katex
tex/  figs/        LaTeX y figuras exportadas
tests/             pytest
config.json        nombre, asignatura y ruta del .tex que muestra la web
```
