# Métodos Matemáticos I · Familias de soluciones de EDOs

**César Acosta** — resolución de las hojas de problemas de ecuaciones diferenciales ordinarias, con gráficas de
todas las curvas integrales, soluciones paramétricas y trayectorias ortogonales.

Este repositorio tiene tres piezas que comparten los mismos datos:

| Pieza | Para qué | Dónde |
|---|---|---|
| **Paquete Python `edoviz`** + **notebook** | Graficar con funciones (matplotlib) y exportar figuras al LaTeX | `edoviz/`, `notebooks/edo_graficas.ipynb` |
| **Web interactiva** (GitHub Pages) | Ver la resolución de cada hoja y mover las constantes con sliders | `docs/` |
| **LaTeX** | Tus resoluciones (`tex/main.tex`) y una entrega por hoja con las figuras (`tex/Hoja_N.tex`) | `tex/`, `figs/` |

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
plot_problem("h4-11-a", field=True, yp=1)                 # 2.º orden: arcos y''(x,y) de las soluciones con y'=1
plot_problem("h4-11-a", phase=True)                       # 2.º orden: diagrama de fases (y, y')
# órdenes superiores (h3-15, h3-16): no hay campo, field=True se ignora

# solo tienes la EDO (sin resolver): integración numérica + campo de direcciones
plot_ode(slope="sin(x-y)", highlight=(0, 1))

interactive("h3-17")                                    # sliders dentro de Jupyter
```

Las expresiones son texto: `+ - * / ^`, `sin cos tan asin acos atan sinh cosh tanh exp log(=ln) sqrt cbrt abs sign min max`,
constantes `pi` y `e`. No hay multiplicación implícita (`2*x`, no `2x`).

## Figuras y entregas en LaTeX

La carpeta `tex/` tiene 6 archivos:

| Archivo | Qué es |
|---|---|
| `main.tex` | Tus resoluciones de todas las hojas, **sin gráficas** (es lo que se previsualiza en la web) |
| `Hoja_1.tex` … `Hoja_6.tex` | Una hoja por archivo, para entregar: sin `\section{Hoja N}`, con fecha, la nota del enlace a la web y las figuras |

Los `Hoja_N.tex` **se generan** a partir de `main.tex`; no se editan a mano:

```bash
python scripts/export_figures.py --patch   # figuras figs/*.pdf  +  tex/Hoja_N.tex
python scripts/split_sheets.py             # solo los tex/Hoja_N.tex (las figuras ya existen)
```

`figs/` contiene un PDF vectorial por ejercicio (`figs/h1-01.pdf … h6-07.pdf`) y uno **por inciso** cuando los hay:
`figs/h4-11-a.pdf`, `h4-11-b.pdf`… (cada uno se inserta justo debajo de su inciso). Los `Hoja_N.tex` buscan las figuras en
`figs/` (Overleaf: sube la carpeta `figs` junto al `.tex`) o en `../figs/` (este repositorio). Las fechas de entrega y la URL de
la web están al principio de `scripts/split_sheets.py` (`DATES`, `URL`).
Opciones de `export_figures.py`: `--sheets 3`, `--png`. Desde Python: `export_figures(...)`, `patch_latex(...)`;
constantes concretas por ejercicio con `values={"h3-17": {"a": 2, "C": 8}}`.

## La web

Abre `docs/index.html` a través de un servidor local (el navegador no deja leer los JSON desde `file://`):

```bash
python scripts/build_site.py          # regenera docs/data/*.json desde el .tex y el catálogo
python -m http.server -d docs 8000    # http://localhost:8000
```

En cada ejercicio: **sliders** por constante (la curva elegida se resalta en trazo grueso sobre la familia completa),
**clic** en el gráfico para elegir la curva que pasa por ese punto, **rueda** para ampliar, **arrastrar** para mover,
campo de direcciones, soluciones singulares/particulares y **Descargar PNG**. Enlaces directos: `#hoja-3/17`.

En las EDO de **2.º orden** el campo de direcciones se sustituye por el *campo de arcos* (en cada punto, la curvatura y″ de la solución
con pendiente y′ fijada con un deslizador) y por el **diagrama de fases** (y, y′); en órdenes superiores no se ofrece ninguno.
En la **Hoja 5** (series de potencias) y la **Hoja 6** (series de Frobenius) un deslizador elige cuántos términos N de la serie se dibujan (por defecto, un número alto). En la Hoja 6 las constantes son los $a_0$ de cada solución y la gráfica vale a ambos lados de $x=0$ (prefactor $|x|^m$); en el problema 7 la recurrencia usa la suma de Cauchy del producto con $e^{-\alpha x}$.

### Vista previa del PDF en la página de inicio

Debajo de las tarjetas de las hojas se ve `docs/main.pdf` (visor con pdf.js, incluido en `docs/vendor/pdfjs`). Ese PDF se genera desde
`tex/main.tex`, así que **cada vez que cambies `main.tex`** ejecuta (necesita `pdflatex`) y sube `docs/main.pdf`:

```bash
python scripts/build_pdf.py
```

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

## Añadir una hoja (o un ejercicio) nuevo

1. Escribe la resolución en `tex/main.tex` bajo `\section{Hoja 7}`, con el mismo formato (`\noindent\textbf{1. ...}` o `\noindent {\bfseries 1. ...}`).
2. Añade una entrada por ejercicio en `edoviz/catalog.py`. Copia una parecida; los tipos son `level` (implícita),
   `explicit`, `param` y `ortho`:
   ```python
   level("h8-01", "x^2*y", K("C", -5, 5, 1), [-4, 4, -4, 4], r"x^2y=C", slope="-2*y/x")
   explicit("h8-02", "C*exp(2*x)", [K("C", -3, 3, 1)], [-2, 2, -6, 6], r"y=Ce^{2x}", slope="2*y")
   ```
   Series de potencias (Hoja 5): `series=[{init, rec}]` define cada serie por su recurrencia y la expresión usa `S(i, x, N)`
   (suma de los N primeros términos); mira `h5-0x` en el catálogo. Series de Frobenius (Hoja 6): igual, con prefactor `abs(x)^m` en la expresión (`h6-0x`);
   `conv: "q"` en la serie hace que `c1` sea la suma de Cauchy $\sum_j q^j/j!\,a_{n-1-j}$ (producto con $e^{qx}$).
3. Regenera: `python scripts/export_figures.py --patch`, `python scripts/build_site.py` y `python scripts/build_pdf.py`.
   Añade la fecha de la hoja en `DATES` de `scripts/split_sheets.py`.

## Estructura

```
edoviz/            paquete Python (expr, catalog, plotting, check, export, texparse, widgets)
notebooks/         edo_graficas.ipynb (generado por scripts/make_notebook.py)
scripts/           build_site.py · export_figures.py · split_sheets.py · build_pdf.py · make_notebook.py
docs/              la web (GitHub Pages): index.html, main.pdf, css/, js/, data/, vendor/katex y pdfjs
tex/  figs/        main.tex + Hoja_1..6.tex (generados) y figuras exportadas
tests/             pytest
config.json        nombre, asignatura y ruta del .tex que muestra la web
```
