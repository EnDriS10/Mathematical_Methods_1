"""Catálogo de problemas graficables (Métodos Matemáticos I).

Cada problema es un *diccionario* (``spec``) con datos puros: expresiones como
texto, rangos de constantes, ventana... Python (``edoviz.plotting``) y la web
(``docs/js``) leen exactamente la misma especificación; por eso añadir una hoja
nueva consiste solo en añadir entradas aquí.

Tipos de ``kind``:
  level     curvas de nivel F(x,y)=C           (soluciones implícitas)
  explicit  y = f(x; constantes)               (admite lista [y+, y-])
  param     x(t), y(t) con parámetro ``var``   (EDOs de Lagrange/Clairaut...)
  ortho     dos familias F1=a, F2=C            (trayectorias ortogonales)

Forma analítica (opcional): los problemas ``level`` y las dos familias de ``ortho`` pueden llevar
``analytic=[frag, ...]`` con la solución despejada (``ex(...)`` = y=f(x), ``pa(...)`` = x(t), y(t)).
El graficador usa esa forma exacta por defecto (``method="analytic"``); con ``method="numeric"``
dibuja las curvas de nivel de F (contornos). Si no hay forma analítica se usa F.

Campos comunes: window [x0,x1,y0,y1], consts, extras (curvas singulares),
particular (solución de un problema de valor inicial), slope (y'=f(x,y), para
el campo de direcciones; si no hay, se resuelve la ``ode`` en y1 por raíces, o se usan las
tangentes de la curva elegida cuando la EDO es de orden superior) y ode (residuo de la EDO en x,y,y1,y2,y3; sirve para
validar la solución con ``edoviz.check``).
"""
from __future__ import annotations

import math
from collections import OrderedDict

PI = math.pi
SPECS: "OrderedDict[str, dict]" = OrderedDict()


def K(name, lo, hi, value, n=13, sweep=True, step=None, role=None, integer=False, spacing="uniform", label=None):
    """Constante ajustable (slider). ``role='level'`` = valor de la curva de nivel."""
    d = dict(name=name, min=lo, max=hi, value=value, sweep=sweep, n=n, spacing=spacing,
             step=step if step is not None else (1 if integer else round((hi - lo) / 200, 4)))
    if role:
        d["role"] = role
    if integer:
        d["integer"] = True
    if label:
        d["label"] = label
    return d


def _add(id_, kind, tex, window, consts, **kw):
    sheet = int(id_[1])
    num = int(id_.split("-")[1])
    part = id_.split("-")[2] if id_.count("-") > 1 else None      # inciso: "h4-11-a" -> "a"
    spec = dict(id=id_, sheet=sheet, num=num, kind=kind, tex=tex, window=list(window), consts=consts)
    if part:
        spec["part"] = part
    spec.update({k: v for k, v in kw.items() if v is not None})
    SPECS[id_] = spec
    return spec


def level(id_, F, C, window, tex, params=(), **kw):
    c = dict(C)
    c.setdefault("role", "level")
    return _add(id_, "level", tex, window, [c, *params], F=F, **kw)


def explicit(id_, y, consts, window, tex, **kw):
    return _add(id_, "explicit", tex, window, consts, y=y, **kw)


def param(id_, x, y, var, t, consts, window, tex, **kw):
    return _add(id_, "param", tex, window, consts, x=x, y=y, var=var, t=t, **kw)


def ortho(id_, F1, F2, consts, window, tex, a1=None, a2=None, **kw):
    main = dict(F=F1, level=consts[0]["name"])
    orth = dict(F=F2, level=consts[1]["name"])
    if a1:
        main["analytic"] = a1
    if a2:
        orth["analytic"] = a2
    return _add(id_, "ortho", tex, window, consts, main=main, ortho=orth, aspect="equal", **kw)


def ex(y, valid=None):
    """Fragmento analítico explícito y=f(x) (``y`` puede ser lista de ramas)."""
    d = dict(kind="explicit", y=y)
    if valid:
        d["valid"] = valid
    return d


def pa(x, y, var, t):
    """Fragmento analítico paramétrico x(var), y(var); ``t=[lo, hi]`` o lista de intervalos."""
    return dict(kind="param", x=x, y=y, var=var, t=t if isinstance(t[0], (list, tuple)) else [list(t)])


def hline(y, label=None):
    return dict(kind="explicit", y=str(y), label=label)


def vline(x, label=None):
    return dict(kind="vline", x=str(x), label=label)


# =====================================================================  HOJA 1
level("h1-01", "atan(x)+atan(y)", K("C", -3, 3, 0.8), [-6, 6, -6, 6],
      r"\arctan x+\arctan y=C", slope="-(1+y^2)/(1+x^2)",
      analytic=[ex("tan(C-atan(x))", valid="pi/2-abs(C-atan(x))")])

level("h1-02", "x^2*(1+y^2)", K("K", 0.1, 6, 2), [-4, 4, -4, 4],
      r"x^2(1+y^2)=K,\;K\geq 0", slope="-(1+y^2)/(x*y)",
      extras=[vline(0, "K=0: x=0")],
      analytic=[pa("sqrt(K/(1+t^2))", "t", "t", [-7, 7]), pa("-sqrt(K/(1+t^2))", "t", "t", [-7, 7])])

explicit("h1-03", "K*sin(x)", [K("K", -3, 3, 1)], [-7, 7, -3.5, 3.5],
         r"y=K\sin x", slope="y*cos(x)/sin(x)", ode="y1*sin(x)-y*cos(x)",
         particular=dict(values={"K": 1}, point=["pi/2", "1"], label="y(π/2)=1"))

level("h1-04", "sqrt(1+x^2)+sqrt(1+y^2)", K("C", 2, 7, 4), [-5, 5, -5, 5],
      r"\sqrt{1+x^2}+\sqrt{1+y^2}=C,\;C\geq 2", slope="-x*sqrt(1+y^2)/(y*sqrt(1+x^2))",
      analytic=[ex(["sqrt((C-sqrt(1+x^2))^2-1)", "-sqrt((C-sqrt(1+x^2))^2-1)"], valid="C-sqrt(1+x^2)-1")])

explicit("h1-05", ["sqrt(1-(C-sqrt(1-x^2))^2)", "-sqrt(1-(C-sqrt(1-x^2))^2)"], [K("C", 0.05, 2, 1)],
         [-1.2, 1.2, -1.2, 1.2], r"\sqrt{1-x^2}+\sqrt{1-y^2}=C", valid="C-sqrt(1-x^2)",
         slope="-x*sqrt(1-y^2)/(y*sqrt(1-x^2))", aspect="equal",
         particular=dict(values={"C": 1}, point=["0", "1"], label="y(0)=1"))

level("h1-06", "(1-exp(-y))/exp(x)", K("C", -3, 3, 1), [-4, 3, -4, 4],
      r"1-e^{-y}=\pm Ke^{x}", slope="exp(y)-1",
      analytic=[ex("-log(1-C*exp(x))")])

level("h1-07", "x*log(y)", K("C", -3, 3, 1), [-4, 4, 0.02, 5],
      r"x\ln y=K", slope="-y*log(y)/x",
      particular=dict(curve=hline(1), point=["1", "1"], label="y(1)=1"),
      analytic=[ex("exp(C/x)")])

level("h1-08", "a^x+a^(-y)", K("K", 0.2, 8, 3, n=12),
      [-4, 4, -4, 4], r"a^x+a^{-y}=K,\;K>0",
      params=[K("a", 0.2, 4, 2, sweep=False, step=0.05)], slope="a^(x+y)",
      analytic=[ex("-log(K-a^x)/log(a)")])

level("h1-09", "2/(1-tan((x-y)/2))-x", K("C", -8, 8, 0), [-7, 7, -7, 7],
      r"\dfrac{2}{1-\tan\frac{x-y}{2}}=x+C", slope="sin(x-y)",
      extras=[hline(f"x-pi/2-2*pi*({k})", "y=x−π/2−2kπ" if k == 0 else None) for k in range(-2, 3)],
      analytic=[ex(f"x-2*atan(1-2/(x+C))-2*pi*({k})-2*pi*sel(x+C,1,0)") for k in range(-3, 4)])

level("h1-10", "(a+b*(a*x+b*y+c))*exp(-b*x)", K("C", -6, 6, 1), [-4, 4, -6, 6],
      r"a+b(ax+by+c)=\pm Ke^{bx}", slope="a*x+b*y+c",
      params=[K("a", -3, 3, 1, sweep=False, step=0.1), K("b", -2, 2, 1, sweep=False, step=0.1),
              K("c", -3, 3, 0, sweep=False, step=0.1)],
      analytic=[ex("(C*exp(b*x)-a-b*(a*x+c))/b^2")])

level("h1-11", "(1+x*y)*exp(-a*x)", K("K", -3, 3, 0.5), [-4, 4, -4, 4],
      r"1+xy=Ke^{ax}", slope="(a*(1+x*y)-y)/x",
      params=[K("a", -2, 2, 1, sweep=False, step=0.1)],
      particular=dict(curve=dict(kind="explicit", y="-1/x"), point=["1/a", "-a"], label="y(1/a)=−a"),
      analytic=[ex("(K*exp(a*x)-1)/x")])

explicit("h1-12", "2*atan(C*exp(2*sin(x)))", [K("C", -4, 4, 1)], [-7, 7, -4, 4],
         r"\tan\frac{y}{2}=Ce^{2\sin x}", slope="2*cos(x)*sin(y)",
         extras=[hline("pi", "y=±π"), hline("-pi")],
         particular=dict(values={"C": 1}, point=["pi", "pi/2"], label="y(π)=π/2"))

explicit("h1-13", "atan(atan(x)+C)/2+k*pi/2",
         [K("C", -3, 3, PI / 2), K("k", 0, 10, 7, integer=True, n=11, label="rama k")], [-8, 8, -0.5, 16],
         r"\tan 2y=\arctan x+C", slope="cos(2*y)^2/(2*(1+x^2))",
         extras=[hline(f"pi/4+{j}*pi/2", "cos 2y=0" if j == 0 else None) for j in range(0, 10)],
         particular=dict(values={"C": PI / 2, "k": 7}, label="y→7π/2 (x→−∞)"))

explicit("h1-14", "K*exp(x^2)-pi", [K("K", -2, 2, 0.4)], [-2, 2, -9, 4],
         r"y=\pm Ke^{x^2}-\pi", slope="2*x*(pi+y)",
         particular=dict(values={"K": 0}, label="y acotada: K=0"))

explicit("h1-15", "x*(atan(log(abs(x))+C)+k*pi)",
         [K("C", -3, 3, 0), K("k", -2, 2, 0, integer=True, n=5, label="rama k")], [-6, 6, -10, 10],
         r"\tan\frac{y}{x}=\ln|x|+C", slope="y/x+cos(y/x)^2",
         extras=[hline(f"x*(pi/2+({j})*pi)", "y=x(π/2+kπ)" if j == 0 else None) for j in range(-2, 2)])

explicit("h1-16", "x*exp(1+K*x)", [K("K", -1.5, 1.5, 0.5)], [0, 5, 0, 8],
         r"y=xe^{1+Kx}", slope="(y/x)*log(y/x)")

explicit("h1-17", "x-2*x/(log(abs(x))+C)", [K("C", -4, 4, 0)], [-6, 6, -6, 6],
         r"\dfrac{2x}{x-y}=\ln|x|+C", slope="(x^2+y^2)/(2*x^2)",
         extras=[hline("x", "y=x (singular)")])

level("h1-18", "2*x^2-3*x*y+y^2", K("C", -10, 10, 4), [-5, 5, -5, 5],
      r"2x^2-3xy+y^2=C", slope="(4*x-3*y)/(3*x-2*y)",
      analytic=[ex(["(3*x+sqrt(x^2+4*C))/2", "(3*x-sqrt(x^2+4*C))/2"])])

explicit("h1-19", "1+(x-1)*(log(abs(x-1))+C)", [K("C", -3, 3, 0)], [-3, 5, -6, 8],
         r"y=1+(x-1)(\ln|x-1|+C)", slope="(2-x-y)/(1-x)")

level("h1-20", "(y-x+1)^2*(y+x-1)^5", K("C", -60, 60, 5, n=14, spacing="symlog"), [-3, 5, -4, 4],
      r"(y-x+1)^2(y+x-1)^5=C", slope="(3*y-7*x+7)/(3*x-7*y-3)",
      extras=[hline("x-1", "y=x−1"), hline("1-x", "y=1−x")],
      analytic=[pa("1+(sel(C,1,-1)*abs(C)^(1/5)*exp(-2*s/5)-exp(s))/2", "(exp(s)+sel(C,1,-1)*abs(C)^(1/5)*exp(-2*s/5))/2", "s", [-20, 3]),
                pa("1+(sel(C,1,-1)*abs(C)^(1/5)*exp(-2*s/5)+exp(s))/2", "(sel(C,1,-1)*abs(C)^(1/5)*exp(-2*s/5)-exp(s))/2", "s", [-20, 3])])

# =====================================================================  HOJA 2
level("h2-01", "(4*x+2*y)^2+4*x+4*y", K("C", -20, 20, 4), [-4, 4, -6, 6],
      r"(4x+2y)^2+4x+4y=C", slope="-(8*x+4*y+1)/(4*x+2*y+1)",
      analytic=[ex(["(-(4*x+1)+sqrt(4*x+1+C))/2", "(-(4*x+1)-sqrt(4*x+1+C))/2"])])

level("h2-02", "(x-2*y)*exp(-(x+3*y))", K("C", -2, 2, 0.5), [-4, 4, -4, 4],
      r"x-2y=\pm Ke^{x+3y}", slope="-(x-2*y-1)/(3*x-6*y+2)",
      analytic=[pa("(3*C*exp(s)+2*s)/5", "(s-C*exp(s))/5", "s", [-14, 14])])

explicit("h2-03", "exp(-x)+C*exp(-2*x)", [K("C", -3, 3, 1)], [-2, 3, -4, 8],
         r"y=e^{-x}+Ce^{-2x}", slope="exp(-x)-2*y")

explicit("h2-04", "C*x-x^2", [K("C", -3, 3, 1)], [-3, 4, -8, 6],
         r"y=Cx-x^2", slope="(y-x^2)/x", ode="x^2+x*y1-y",
         particular=dict(values={"C": 1}, point=["1", "0"], label="y(1)=0"))

explicit("h2-05", "(x^2+C)/cos(x)", [K("C", -3, 3, 0)], [-4, 4, -8, 8],
         r"y=(x^2+C)\sec x", ode="y1*cos(x)-y*sin(x)-2*x",
         particular=dict(values={"C": 0}, point=["0", "0"], label="y(0)=0"),
      slope="(y*sin(x)+2*x)/cos(x)")

explicit("h2-06", "x^2*(sin(x)+C)", [K("C", -3, 3, 0.5)], [-6, 6, -30, 30],
         r"y=x^2(\sin x+C)", ode="x*y1-2*y-x^3*cos(x)",
      slope="(2*y+x^3*cos(x))/x")

param("h2-07", "(K*t-t^2)/2", "t", "t", [[-6, 6]], [K("K", -4, 4, 1)], [-8, 6, -5, 5],
      r"2x+y^2=Ky", slope="2*y/(2*x-y^2)", ode="(2*x-y^2)*y1-2*y",
      extras=[hline(0, "y=0 (K→∞)")])

param("h2-08", "t*log(t)+K/t", "t", "t", [[0.03, 6]], [K("K", -3, 3, 1)], [-5, 8, 0, 5],
      r"x=y\ln y+\dfrac{K}{y}", slope="y/(2*y*log(y)+y-x)", ode="y1*(2*y*log(y)+y-x)-y")

param("h2-09", "(t+C)*exp(-t^2/2)", "t", "t", [[-5, 5]], [K("C", -3, 3, 1)], [-4, 4, -4, 4],
      r"xe^{y^2/2}-y=C", slope="1/(exp(-y^2/2)-x*y)", ode="(exp(-y^2/2)-x*y)*y1-1")

explicit("h2-10", "2^sin(x)+C*2^x", [K("C", -0.6, 0.6, 0.2)], [-6, 4, -6, 14],
         r"y=2^{\sin x}+C\,2^{x}", slope="y*log(2)+2^sin(x)*(cos(x)-1)*log(2)",
         particular=dict(values={"C": 0}, label="y acotada: C=0"))

explicit("h2-11", "1/(1+C*exp(x^2))", [K("C", -3, 3, 1)], [-3, 3, -3, 3],
         r"y=\dfrac{1}{1+Ce^{x^2}}", slope="2*x*y*(y-1)", extras=[hline(0, "y=0")])

param("h2-12", "cbrt((t+C)*exp(t))", "t", "t", [[-5, 4]], [K("C", -3, 3, 0)], [-4, 4, -4, 4],
      r"x^3=(y+C)e^y", slope="3*x^2/(x^3+exp(y))", ode="(x^3+exp(y))*y1-3*x^2")

explicit("h2-13", "(C*exp(exp(x))-1)^2", [K("C", 0.05, 3, 1)], [-3, 2, 0, 12],
         r"y=(Ce^{e^x}-1)^2", valid="C*exp(exp(x))-1", extras=[hline(0, "y=0")],
         ode="y1-2*y*exp(x)-2*sqrt(y)*exp(x)",
      slope="2*exp(x)*(y+sqrt(y))")

explicit("h2-14", ["sqrt((sin(x)+C)/log(x))", "-sqrt((sin(x)+C)/log(x))"], [K("C", -2, 2, 0.5)], [0, 8, -4, 4],
         r"y^2=\dfrac{\sin x+C}{\ln x}", ode="2*y*y1*log(x)+y^2/x-cos(x)",
      slope="(cos(x)-y^2/x)/(2*y*log(x))")

explicit("h2-15", ["1/sqrt((C-x)*sin(x))", "-1/sqrt((C-x)*sin(x))"], [K("C", -2, 10, 6)], [-2, 10, -4, 4],
         r"y^2=\dfrac{1}{(C-x)\sin x}", ode="2*y1*sin(x)+y*cos(x)-y^3*sin(x)^2",
      slope="(y^3*sin(x)^2-y*cos(x))/(2*sin(x))")

explicit("h2-16", "C/x", [K("C", -4, 4, 1)], [-5, 5, -5, 5], r"y=\pm\dfrac{C}{x}", slope="-y/x")

explicit("h2-17", "C*x^((1-n)/n)", [K("C", -3, 3, 1)], [0, 5, -5, 5],
         r"y=Cx^{\frac{1-n}{n}}", slope="(1-n)/n*y/x",
         ) ["consts"].append(K("n", 0.3, 4, 2, sweep=False, step=0.1))

level("h2-18", "x^4+x^2*y^2+y^4", K("C", 0.2, 30, 5, n=10, spacing="geom"), [-3, 3, -3, 3],
      r"x^4+x^2y^2+y^4=C", slope="-x*(2*x^2+y^2)/(y*(x^2+2*y^2))",
      analytic=[ex(["sqrt((sqrt(4*C-3*x^4)-x^2)/2)", "-sqrt((sqrt(4*C-3*x^4)-x^2)/2)"])])

level("h2-19", "sqrt(x^2+y^2)+log(abs(x*y))+x/y", K("C", -6, 6, 1), [-4, 4, -4, 4],
      r"\sqrt{x^2+y^2}+\ln|xy|+\dfrac{x}{y}=C",
      slope="-(x/sqrt(x^2+y^2)+1/x+1/y)/(y/sqrt(x^2+y^2)+1/y-x/y^2)")

level("h2-20", "x^3*tan(y)+y^3/x^2+y^4", K("C", -10, 10, 1), [-3, 3, -1.5, 1.5],
      r"x^3\tan y+\dfrac{y^3}{x^2}+y^4=C",
      slope="-(3*x^2*tan(y)-2*y^3/x^3)/(x^3/cos(y)^2+4*y^3+3*y^2/x^2)")

# =====================================================================  HOJA 3
explicit("h3-01", "cbrt(x^2*(C-x*log(x)+x))", [K("C", -6, 6, 1)], [0, 5, -6, 6],
         r"\dfrac{y^3}{x^2}+x\ln x-x=C", ode="(x^4*log(x)-2*x*y^3)+3*x^2*y^2*y1",
      slope="(2*x*y^3-x^4*log(x))/(3*x^2*y^2)")

level("h3-02", "(sin(y)+x-1+(sin(x)-cos(x))/2)*exp(x)", K("C", -60, 60, 5, n=14, spacing="symlog"),
      [-4, 4, -4, 4], r"\sin y+x-1+\tfrac{\sin x-\cos x}{2}=Ce^{-x}", slope="-(x+sin(x)+sin(y))/cos(y)",
      analytic=[ex("asin(g)"), ex("pi-asin(g)"), ex("-pi-asin(g)")],
      defs=[["g", "C*exp(-x)-x+1-(sin(x)-cos(x))/2"]])

param("h3-03", "(p+1)*exp(p)+C", "p^2*exp(p)", "p", [[-12, 2.2]], [K("C", -4, 4, 0)], [-6, 8, -1, 10],
      r"x=(p+1)e^p+C,\;y=p^2e^p", ode="y-y1^2*exp(y1)", extras=[hline(0, "y=0")])

param("h3-04", "log(p)+sin(p)", "p+p*sin(p)+cos(p)+C", "p", [[0.02, 12]], [K("C", -6, 6, 0)], [-4, 5, -6, 16],
      r"x=\ln p+\sin p,\;y=p+p\sin p+\cos p+C", ode="x-log(y1)-sin(y1)")

param("h3-05", "a*cos(th)^3", "C-a*sin(th)^3", "th", [[-PI / 2, PI / 2]],
      [K("a", 0.5, 3, 1, n=6, step=0.05), K("C", -3, 3, 0, n=7)], [-1, 4, -5, 5],
      r"x=a\cos^3\theta,\;y=C-a\sin^3\theta", ode="x*(1+y1^2)^(3/2)-a", aspect="equal")

param("h3-06", "p+sin(p)", "p^2/2+p*sin(p)+cos(p)+C", "p", [[-9, 9]], [K("C", -6, 6, 0)], [-10, 10, -5, 45],
      r"x=p+\sin p,\;y=\tfrac{p^2}{2}+p\sin p+\cos p+C", ode="x-y1-sin(y1)")

param("h3-07", "(C-p)/p^2", "2*(C-p)/p+log(p)", "p", [[0.06, 8]], [K("C", -3, 3, 1)], [-3, 6, -6, 8],
      r"x=\dfrac{C-p}{p^2},\;y=\dfrac{2(C-p)}{p}+\ln p", ode="y-2*x*y1-log(y1)")

param("h3-08", "(C-p*sin(p)-cos(p))/p^2", "2*(C-cos(p))/p-sin(p)", "p", [[0.1, 14], [-14, -0.1]],
      [K("C", -3, 3, 1)], [-6, 6, -8, 8],
      r"x=\dfrac{C-p\sin p-\cos p}{p^2},\;y=\dfrac{2(C-\cos p)}{p}-\sin p", ode="y-2*x*y1-sin(y1)")

param("h3-09", "(2*C*p^2+2*p-1)/(2*p^2*(1-p)^2)", "(2*C*p^2+2*p-1)/(2*(1-p)^2)-1/p", "p",
      [[-8, -0.05], [0.05, 0.95], [1.05, 8]], [K("C", -2, 2, 0.5)], [-6, 6, -6, 6],
      r"x=\dfrac{2Cp^2+2p-1}{2p^2(1-p)^2}", ode="y-x*y1^2+1/y1",
      extras=[hline("x-1", "p=1: y=x−1")])

explicit("h3-10", "C*x+a/C^2", [K("C", -3, 3, 1, n=14), K("a", 0.2, 3, 1, sweep=False, step=0.05)],
         [-6, 6, -4, 8], r"y=Cx+\dfrac{a}{C^2}", ode="y-x*y1-a/y1^2",
         extras=[hline("3*cbrt(a*x^2/4)", "4y³=27ax² (singular)")])

explicit("h3-11", "C*x+1/C-1", [K("C", -3, 3, 1, n=14)], [-2, 6, -6, 6],
         r"y=Cx+\dfrac{1}{C}-1", ode="x*y1^2-y*y1-y1+1",
         extras=[hline("2*sqrt(x)-1", "(y+1)²=4x (singular)"), hline("-2*sqrt(x)-1")])

explicit("h3-12", "exp(x)+1/(exp(x)+C)", [K("C", -3, 3, 1)], [-3, 3, -2, 10],
         r"y=e^x+\dfrac{1}{e^x+C}", slope="exp(x)*(1-exp(2*x)-y^2+2*y*exp(x))",
         extras=[hline("exp(x)", "y₁=eˣ")])

explicit("h3-13", "sel(abs(D)-1e-9, sel(D, (r1-r2*R)/(1-R), (S*tan(S/2*(C-x))-n)/(2*m)), (2/(x+C)-n)/(2*m))",
         [K("C", -4, 4, 1), K("m", 0.2, 3, 1, sweep=False, step=0.1), K("n", -5, 5, -3, sweep=False, step=0.1),
          K("p", -3, 5, 2, sweep=False, step=0.1)], [-4, 4, -5, 5],
         r"\Delta=n^2-4mp\;\;(\phi\equiv1)", slope="-(m*y^2+n*y+p)",
         check_overrides=[dict(m=1, n=2, p=1), dict(m=2, n=-4, p=2)],   # Δ=0
         defs=[["D", "n^2-4*m*p"], ["S", "sqrt(abs(D))"], ["R", "C*exp(-S*x)"],
               ["r1", "(-n+S)/(2*m)"], ["r2", "(-n-S)/(2*m)"]],
         extras=[hline("sel(D,r1,nan)", "raíces constantes"), hline("sel(D,r2,nan)")])

param("h3-14", "(t^2-C^2)/(2*C)", "t", "t", [[-6, 6]], [K("C", -3, 3, 1.5, n=12)], [-6, 6, -6, 6],
      r"y^2=2Cx+C^2", ode="y*y1^2+2*x*y1-y")

explicit("h3-15", "a*x^2+b*x+c",
         [K("a", -2, 2, 0.5, n=7), K("b", -3, 3, 1, n=7), K("c", -3, 3, -1, n=7)], [-4, 4, -6, 6],
         r"y=ax^2+bx+c", ode="y3")

explicit("h3-16", "C1*x+C2/x+C3",
         [K("C1", -3, 3, 1, n=7), K("C2", -3, 3, 1, n=7), K("C3", -3, 3, 0, n=7)], [-4, 4, -8, 8],
         r"y=C_1x+\dfrac{C_2}{x}+C_3", ode="x*y3+3*y2")

ortho("h3-17", "-y^2/(2*x)", "2*x^2+y^2",
      [K("a", 0.1, 4, 1, n=9, role="level"), K("C", 0.5, 20, 6, n=9, role="level")], [-6, 4, -5, 5],
      r"y^2+2ax=0\;\perp\;2x^2+\tilde y^2=C",
      ode="y1-y/(2*x)", ode_ortho="y*y1+2*x",
      a1=[pa("-t^2/(2*a)", "t", "t", [-9, 9])],
      a2=[pa("sqrt(C/2)*cos(t)", "sqrt(C)*sin(t)", "t", [0, 2 * PI])],
      slope="y/(2*x)")

ortho("h3-18", "y/x^n", "x^2+n*y^2",
      [K("a", -3, 3, 1, n=9, role="level"), K("C", 0.5, 12, 4, n=9, role="level"),
       K("n", 0.5, 4, 2, sweep=False, step=0.5)], [-4, 4, -4, 4],
      r"y=ax^n\;\perp\;x^2+n\tilde y^2=C", ode="y1-n*y/x", ode_ortho="n*y*y1+x",
      a1=[ex("a*x^n")],
      a2=[pa("sqrt(C)*cos(t)", "sqrt(C/n)*sin(t)", "t", [0, 2 * PI])],
      slope="n*y/x")

ortho("h3-19", "y*exp(-k*x)", "k*y^2+2*x",
      [K("a", -3, 3, 1, n=9, role="level"), K("C", -6, 6, 0, n=9, role="level"),
       K("k", -2, 2, 1, sweep=False, step=0.25)], [-4, 4, -4, 4],
      r"y=ae^{kx}\;\perp\;k\tilde y^2+2x=C", ode="y1-k*y", ode_ortho="k*y*y1+1",
      a1=[ex("a*exp(k*x)")],
      a2=[pa("(C-k*t^2)/2", "t", "t", [-9, 9])],
      slope="k*y")

ortho("h3-20", "cos(y)*exp(x)", "sin(y)*exp(x)",
      [K("a", -3, 3, 1, n=9, role="level"), K("C", -3, 3, 1, n=9, role="level")], [-3, 3, -4, 4],
      r"\cos y=ae^{-x}\;\perp\;\sin\tilde y=Ce^{-x}", ode="y1*sin(y)-cos(y)", ode_ortho="y1*cos(y)+sin(y)",
      defs=[["g1", "a*exp(-x)"], ["g2", "C*exp(-x)"]],
      a1=[ex("acos(g1)"), ex("-acos(g1)"), ex("acos(g1)-2*pi"), ex("2*pi-acos(g1)")],
      a2=[ex("asin(g2)"), ex("pi-asin(g2)"), ex("-pi-asin(g2)")],
      slope="cos(y)/sin(y)")

# =====================================================================  HOJA 4
# EDOs lineales de 2.º orden. Soluciones generales y_h = C1·y1 + C2·y2 (+ y_p). Los problemas con incisos
# llevan una gráfica por inciso: h4-11-a, h4-11-b, ... (la web los muestra con un selector).
def _c(lo=-3, hi=3, v1=1, v2=1, n=7):
    return [K("C1", lo, hi, v1, n=n, label="C₁"), K("C2", lo, hi, v2, n=n, label="C₂")]


def _yp0(label="solución particular yₚ"):
    return dict(values={"C1": 0, "C2": 0}, label=label)


explicit("h4-01", "C1+C2*log(x)", _c(), [0, 6, -5, 5], r"y=C_1+C_2\ln x", ode="x*y2+y1")
explicit("h4-02", "C1*x+C2*x^2", _c(), [-3, 3, -8, 8], r"y=c_1x+c_2x^2", ode="x^2*y2-2*x*y1+2*y")
explicit("h4-03", "C1*exp(k*x)+C2*exp(-k*x)", _c() + [K("k", 0.1, 2, 1, sweep=False, step=0.05)], [-3, 3, -8, 8],
         r"y=c_1e^{kx}+c_2e^{-kx}", ode="y2-k^2*y")
explicit("h4-04", "C1*x+C2*sin(x)", _c(), [-7, 7, -8, 8], r"y=c_1x+c_2\sin x",
         ode="(x*cos(x)-sin(x))*y2+x*sin(x)*y1-y*sin(x)")
explicit("h4-06", "C1*exp(x)+C2*exp(-x)", _c(), [-3, 3, -8, 8], r"y=C_1e^{x}+C_2e^{-x}", ode="y2-y")

# 7 · problemas de valor inicial (las constantes arrancan en la solución particular)
explicit("h4-07-a", "C1*exp(x)+C2*exp(-2*x)", _c(-10, 10, 6, 2), [-1, 2.5, -10, 80], r"y=C_1e^{x}+C_2e^{-2x}",
         ode="y2+y1-2*y", particular=dict(values={"C1": 6, "C2": 2}, point=["0", "8"], label="y(0)=8, y′(0)=2"))
explicit("h4-07-b", "C1*exp(x)+C2*exp(-2*x)", _c(-10, 10, 0, 0), [-1, 2.5, -10, 80], r"y=C_1e^{x}+C_2e^{-2x}",
         ode="y2+y1-2*y", particular=dict(values={"C1": 0, "C2": 0}, point=["1", "0"], label="y(1)=0, y′(1)=0"))
explicit("h4-07-c", "C1*exp(-2*x)+C2*exp(-3*x)", _c(-6, 6, 4, -3), [-1, 3, -20, 20], r"y=C_1e^{-2x}+C_2e^{-3x}",
         ode="y2+5*y1+6*y", particular=dict(values={"C1": 4, "C2": -3}, point=["0", "1"], label="y(0)=1, y′(0)=1"))
explicit("h4-07-d", "C1+C2*exp(-x)", _c(-3, 3, math.exp(-2), -1), [-1, 3, -4, 4], r"y=C_1+C_2e^{-x}",
         ode="y2+y1", particular=dict(values={"C1": math.exp(-2), "C2": -1}, point=["2", "0"], label="y(2)=0, y′(2)=1/e²"))

explicit("h4-08", "C1*sin(x)+C2*cos(x)", _c(), [-7, 7, -4, 4], r"y=C_1\sin x+C_2\cos x", ode="y2+y")
explicit("h4-09", "C1+C2/x^2", _c(), [-4, 4, -5, 5], r"y=C_1+\dfrac{C_2}{x^2}", ode="x*y2+3*y1")
explicit("h4-10", "C1*exp(x)+C2*x^2*exp(x)", _c(), [-3, 3, -10, 20], r"y=C_1e^x+C_2x^2e^x",
         ode="x*y2-(2*x+1)*y1+(x+1)*y")

# 11 · coeficientes constantes: (letra, y, EDO, ventana, tex)
for _l, _y, _ode, _w, _t in [
    ("a", "(C1+C2*x)*exp(2*x)", "y2-4*y1+4*y", [-2, 2, -10, 10], r"y=(C_1+C_2x)e^{2x}"),
    ("b", "C1*exp(4*x)+C2*exp(5*x)", "y2-9*y1+20*y", [-1, 1, -10, 10], r"y=C_1e^{4x}+C_2e^{5x}"),
    ("c", "exp(-x/2)*(C1*cos(sqrt(5)/2*x)+C2*sin(sqrt(5)/2*x))", "2*y2+2*y1+3*y", [-4, 6, -6, 6],
     r"y=e^{-x/2}\left(C_1\cos\frac{\sqrt5}{2}x+C_2\sin\frac{\sqrt5}{2}x\right)"),
    ("d", "(C1+C2*x)*exp(3*x/2)", "4*y2-12*y1+9*y", [-2, 2, -10, 10], r"y=(C_1+C_2x)e^{3x/2}"),
    ("e", "C1+C2*exp(-x)", "y2+y1", [-2, 3, -8, 8], r"y=C_1+C_2e^{-x}"),
    ("f", "exp(3*x)*(C1*cos(4*x)+C2*sin(4*x))", "y2-6*y1+25*y", [-2, 1, -10, 10], r"y=e^{3x}(C_1\cos 4x+C_2\sin 4x)"),
    ("g", "(C1+C2*x)*exp(-5*x/2)", "4*y2+20*y1+25*y", [-2, 2, -10, 10], r"y=(C_1+C_2x)e^{-5x/2}"),
    ("h", "exp(-x)*(C1*cos(sqrt(2)*x)+C2*sin(sqrt(2)*x))", "y2+2*y1+3*y", [-3, 4, -8, 8],
     r"y=e^{-x}(C_1\cos\sqrt2x+C_2\sin\sqrt2x)"),
    ("i", "C1*exp(2*x)+C2*exp(-2*x)", "y2-4*y", [-2, 2, -8, 8], r"y=C_1e^{2x}+C_2e^{-2x}"),
    ("j", "exp(x)*(C1*cos(sqrt(3)/2*x)+C2*sin(sqrt(3)/2*x))", "4*y2-8*y1+7*y", [-3, 3, -8, 8],
     r"y=e^{x}\left(C_1\cos\frac{\sqrt3}{2}x+C_2\sin\frac{\sqrt3}{2}x\right)"),
    ("k", "C1*exp(x/2)+C2*exp(-x)", "2*y2+y1-y", [-3, 3, -8, 8], r"y=C_1e^{x/2}+C_2e^{-x}"),
    ("l", "(C1+C2*x)*exp(x/4)", "16*y2-8*y1+y", [-4, 6, -6, 6], r"y=(C_1+C_2x)e^{x/4}"),
    ("m", "exp(-2*x)*(C1*cos(x)+C2*sin(x))", "y2+4*y1+5*y", [-2, 4, -8, 8], r"y=e^{-2x}(C_1\cos x+C_2\sin x)"),
    ("n", "C1*exp(x)+C2*exp(-5*x)", "y2+4*y1-5*y", [-2, 2, -8, 8], r"y=C_1e^{x}+C_2e^{-5x}"),
]:
    explicit(f"h4-11-{_l}", _y, _c(), _w, _t, ode=_ode)

# 12 · problemas de valor inicial
_E = math.exp
for _l, _y, _ode, _w, _t, _v, _pt, _lab, _r in [
    ("a", "C1*exp(2*x)+C2*exp(3*x)", "y2-5*y1+6*y", [-2, 1.8, -5, 60], r"y=C_1e^{2x}+C_2e^{3x}",
     (0, _E(-1)), ("1", "exp(2)"), "y(1)=e², y′(1)=3e²", 4),
    ("b", "C1*exp(x)+C2*exp(5*x)", "y2-6*y1+5*y", [-2, 1, -5, 60], r"y=C_1e^{x}+C_2e^{5x}", (1, 2), ("0", "3"),
     "y(0)=3, y′(0)=11", 4),
    ("c", "(C1+C2*x)*exp(3*x)", "y2-6*y1+9*y", [-1, 1.5, -5, 60], r"y=(C_1+C_2x)e^{3x}", (0, 5), ("0", "0"),
     "y(0)=0, y′(0)=5", 6),
    ("d", "exp(-2*x)*(C1*cos(x)+C2*sin(x))", "y2+4*y1+5*y", [-1, 4, -4, 16], r"y=e^{-2x}(C_1\cos x+C_2\sin x)", (1, 2),
     ("0", "1"), "y(0)=1, y′(0)=0", 4),
    ("e", "C1*exp((-2+sqrt(2))*x)+C2*exp((-2-sqrt(2))*x)", "y2+4*y1+2*y", [-1, 2, -10, 10],
     r"y=C_1e^{(-2+\sqrt2)x}+C_2e^{(-2-\sqrt2)x}", (1, -2), ("0", "-1"), "y(0)=−1, y′(0)=2+3√2", 4),
    ("f", "C1*exp(x-1)+C2*exp(-9*(x-1))", "y2+8*y1-9*y", [0, 3, -1, 12], r"y=C_1e^{x-1}+C_2e^{-9(x-1)}", (9 / 5, 1 / 5),
     ("1", "2"), "y(1)=2, y′(1)=0", 4),
]:
    explicit(f"h4-12-{_l}", _y, [K("C1", -_r, _r, _v[0], n=7, label="C₁"), K("C2", -_r, _r, _v[1], n=7, label="C₂")], _w, _t,
             ode=_ode, particular=dict(values={"C1": _v[0], "C2": _v[1]}, point=list(_pt), label=_lab))

# 13 · Euler (x>0)
for _l, _y, _ode, _w, _t in [
    ("a", "C1*x^(3/2)+C2*x^(-1/2)", "4*x^2*y2-3*y", [0, 4, -8, 8], r"y=C_1x^{3/2}+C_2x^{-1/2}"),
    ("b", "(C1+C2*log(x))*x^2", "x^2*y2-3*x*y1+4*y", [0, 3, -10, 10], r"y=(C_1+C_2\ln x)x^2"),
    ("c", "C1*x^2+C2*x^(-3)", "x^2*y2+2*x*y1-6*y", [0, 3, -10, 10], r"y=C_1x^2+C_2x^{-3}"),
    ("d", "x^(-1/2)*(C1*cos(sqrt(11)/2*log(x))+C2*sin(sqrt(11)/2*log(x)))", "x^2*y2+2*x*y1+3*y", [0, 6, -5, 5],
     r"y=x^{-1/2}\left(C_1\cos\left(\frac{\sqrt{11}}{2}\ln x\right)+C_2\sin\left(\frac{\sqrt{11}}{2}\ln x\right)\right)"),
    ("e", "C1*x^sqrt(2)+C2*x^(-sqrt(2))", "x^2*y2+x*y1-2*y", [0, 4, -8, 8], r"y=C_1x^{\sqrt2}+C_2x^{-\sqrt2}"),
    ("f", "C1*x^4+C2*x^(-4)", "x^2*y2+x*y1-16*y", [0, 2, -8, 8], r"y=C_1x^4+C_2x^{-4}"),
]:
    explicit(f"h4-13-{_l}", _y, _c(), _w, _t, ode=_ode)

explicit("h4-15-a", "exp(-x^2/4)*(C1*cos(sqrt(3)*x^2/4)+C2*sin(sqrt(3)*x^2/4))", _c(), [-5, 5, -4, 4],
         r"y=e^{-x^2/4}\left(C_1\cos\frac{\sqrt3x^2}{4}+C_2\sin\frac{\sqrt3x^2}{4}\right)",
         ode="x*y2+(x^2-1)*y1+x^3*y")

# 16 · no homogéneas (solución general)
for _l, _y, _ode, _w, _t in [
    ("a", "C1*exp(3*x)+C2*exp(-2*x)-4*x*exp(-2*x)", "y2-y1-6*y-20*exp(-2*x)", [-2, 1.5, -15, 15],
     r"y=C_1e^{3x}+C_2e^{-2x}-4xe^{-2x}"),
    ("b", "C1*exp(x)+C2*exp(2*x)+3*cos(2*x)+2*sin(2*x)", "y2-3*y1+2*y-(14*sin(2*x)-18*cos(2*x))", [-3, 1.5, -15, 15],
     r"y=C_1e^{x}+C_2e^{2x}+3\cos 2x+2\sin 2x"),
    ("c", "C1*cos(x)+C2*sin(x)+x*sin(x)", "y2+y-2*cos(x)", [-8, 8, -10, 10], r"y=C_1\cos x+C_2\sin x+x\sin x"),
    ("d", "C1+C2*exp(2*x)-3*x^2+2*x", "y2-2*y1-(12*x-10)", [-3, 3, -20, 20], r"y=C_1+C_2e^{2x}-3x^2+2x"),
    ("e", "(C1+C2*x+3*x^2)*exp(x)", "y2-2*y1+y-6*exp(x)", [-3, 2, -20, 20], r"y=(C_1+C_2x+3x^2)e^x"),
    ("f", "exp(x)*(C1*cos(x)+C2*sin(x))-x*exp(x)*cos(x)/2", "y2-2*y1+2*y-exp(x)*sin(x)", [-5, 3, -15, 15],
     r"y=e^x(C_1\cos x+C_2\sin x)-\tfrac12xe^x\cos x"),
    ("g", "C1+C2*exp(-x)+2*x^5-10*x^4+40*x^3-120*x^2+242*x", "y2+y1-(10*x^4+2)", [-1.2, 2.5, -250, 300],
     r"y=C_1+C_2e^{-x}+2x^5-10x^4+40x^3-120x^2+242x"),
    ("h", "C1*cos(3*x)+C2*sin(3*x)-x*cos(3*x)/3+sin(x)/2-2*exp(-2*x)+3*x^3-2*x",
     "y2+9*y-(2*sin(3*x)+4*sin(x)-26*exp(-2*x)+27*x^3)", [-4, 4, -50, 50],
     r"y=C_1\cos3x+C_2\sin3x-\tfrac13x\cos3x+\tfrac12\sin x-2e^{-2x}+3x^3-2x"),
]:
    explicit(f"h4-16-{_l}", _y, _c(), _w, _t, ode=_ode)

# 17 · variación de parámetros: yₚ + C1·y1 + C2·y2 (la curva destacada en verde es yₚ)
for _l, _yp, _y1, _y2, _ode, _w, _t in [
    ("a", "-cos(2*x)*log(abs(sec(2*x)+tan(2*x)))/4", "cos(2*x)", "sin(2*x)", "y2+4*y-tan(2*x)", [-2, 2, -3, 3],
     r"y''+4y=\tan 2x"),
    ("b", "x^2*exp(-x)*log(x)/2-3*x^2*exp(-x)/4", "exp(-x)", "x*exp(-x)", "y2+2*y1+y-exp(-x)*log(x)", [0, 5, -3, 3],
     r"y''+2y'+y=e^{-x}\ln x"),
    ("c", "(-8*x^2-4*x)*exp(-x)", "exp(3*x)", "exp(-x)", "y2-2*y1-3*y-64*x*exp(-x)", [-2, 2, -30, 30],
     r"y''-2y'-3y=64xe^{-x}"),
    ("d", "exp(-x)*(cos(2*x)*log(abs(cos(2*x)))/4+x*sin(2*x)/2)", "exp(-x)*cos(2*x)", "exp(-x)*sin(2*x)",
     "y2+2*y1+5*y-exp(-x)*sec(2*x)", [-1.5, 3, -4, 4], r"y''+2y'+5y=e^{-x}\sec 2x"),
    ("e", "exp(-3*x)/10", "exp(-x/2)", "exp(-x)", "2*y2+3*y1+y-exp(-3*x)", [-1, 3, -3, 3], r"2y''+3y'+y=e^{-3x}"),
    ("f", "(exp(x)+exp(2*x))*log(1+exp(-x))-exp(x)", "exp(x)", "exp(2*x)", "y2-3*y1+2*y-1/(1+exp(-x))", [-3, 3, -6, 12],
     r"y''-3y'+2y=\dfrac{1}{1+e^{-x}}"),
]:
    explicit(f"h4-17-{_l}", f"({_yp})+C1*({_y1})+C2*({_y2})", _c(-2, 2, 0, 0, n=5), _w, _t, ode=_ode, particular=_yp0())

# 18 · y'' + y = f(x): yₚ + C1 cos x + C2 sin x
for _l, _yp, _f, _w, _t in [
    ("a", "cos(x)*log(abs(cos(x)))+x*sin(x)", "1/cos(x)", [-6.3, 6.3, -6, 6], r"y''+y=\sec x"),
    ("b", "cos(x)*log(abs(csc(x)+cot(x)))-2", "cos(x)^2/sin(x)^2", [-6.3, 6.3, -6, 6], r"y''+y=\cot^2x"),
    ("c", "cos(x)*log(abs(sec(x)+tan(x)))/2-sin(x)*log(abs(csc(x)+cot(x)))/2", "cos(2*x)/sin(2*x)", [-6.3, 6.3, -6, 6],
     r"y''+y=\cot 2x"),
    ("d", "x^2*sin(x)/4+x*cos(x)/4", "x*cos(x)", [-8, 8, -12, 12], r"y''+y=x\cos x"),
    ("e", "-cos(x)*log(abs(sec(x)+tan(x)))", "tan(x)", [-6.3, 6.3, -6, 6], r"y''+y=\tan x"),
    ("f", "x*cos(x)+sin(x)*log(abs(sec(x)))", "sin(x)/cos(x)^2", [-6.3, 6.3, -6, 6], r"y''+y=\sec x\tan x"),
    ("g", "-cos(x)*log(abs(sec(x)+tan(x)))-sin(x)*log(abs(csc(x)+cot(x)))", "1/(cos(x)*sin(x))", [-6.3, 6.3, -6, 6],
     r"y''+y=\sec x\csc x"),
]:
    explicit(f"h4-18-{_l}", f"({_yp})+C1*cos(x)+C2*sin(x)", _c(-2, 2, 0, 0, n=5), _w, _t, ode=f"y2+y-({_f})",
             particular=_yp0())


def sheet_ids(n: int):
    return [k for k, v in SPECS.items() if v["sheet"] == n]


def get(id_: str) -> dict:
    if id_ not in SPECS:
        raise KeyError(f"Problema {id_!r} no está en el catálogo. Ejemplos: {list(SPECS)[:3]}...")
    return SPECS[id_]
