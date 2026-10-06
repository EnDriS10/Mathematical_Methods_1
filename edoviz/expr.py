"""Compilador seguro de expresiones matemáticas (texto -> función de numpy).

La misma gramática la implementa ``docs/js/engine.js`` para la web, de modo que
una expresión escrita una sola vez (p. ej. ``"atan(x)+atan(y)"``) se evalúa
igual en Python y en el navegador.

Gramática (precedencia de menor a mayor)::

    expr   := term (('+'|'-') term)*
    term   := unary (('*'|'/') unary)*
    unary  := ('-'|'+') unary | power
    power  := atom ('^' unary)?          # asociativa por la derecha: 2^-x^2
    atom   := número | nombre | nombre '(' args ')' | '(' expr ')'

No hay multiplicación implícita: escribe ``2*x``, no ``2x``.
"""
from __future__ import annotations

import re
from typing import Callable, Iterable, Sequence

import numpy as np

# nombre -> código Python que lo implementa
FUNCS = {
    "sin": "np.sin", "cos": "np.cos", "tan": "np.tan",
    "asin": "np.arcsin", "acos": "np.arccos", "atan": "np.arctan",
    "atan2": "np.arctan2",
    "sinh": "np.sinh", "cosh": "np.cosh", "tanh": "np.tanh",
    "asinh": "np.arcsinh", "acosh": "np.arccosh", "atanh": "np.arctanh",
    "exp": "np.exp", "log": "np.log", "log10": "np.log10", "log2": "np.log2",
    "sqrt": "np.sqrt", "cbrt": "np.cbrt", "abs": "np.abs", "sign": "np.sign",
    "floor": "np.floor", "ceil": "np.ceil",
    "min": "np.minimum", "max": "np.maximum",
    "sec": "_sec", "csc": "_csc", "cot": "_cot", "sel": "_sel",
}
# alias en castellano / otras convenciones
ALIASES = {
    "ln": "log", "sen": "sin", "tg": "tan", "arctan": "atan", "arcsin": "asin",
    "arccos": "acos", "sh": "sinh", "ch": "cosh", "th": "tanh", "arcsen": "asin",
    "arctg": "atan",
}
CONSTS = {"pi": "np.pi", "e": "np.e", "nan": "np.nan", "inf": "np.inf"}

_TOKEN = re.compile(r"\s*(?:(\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+)|([A-Za-z_]\w*)|(\*\*|[-+*/^(),]))")


def _sec(x): return 1.0 / np.cos(x)
def _csc(x): return 1.0 / np.sin(x)
def _cot(x): return 1.0 / np.tan(x)
def _sel(c, a, b):
    """sel(c, a, b): a donde c > 0, b en el resto (equivalente a un if vectorizado)."""
    return np.where(np.asarray(c) > 0, a, b)


class ExprError(ValueError):
    pass


def _tokenize(s: str):
    pos, out = 0, []
    s = s.strip()
    while pos < len(s):
        m = _TOKEN.match(s, pos)
        if not m or m.end() == pos:
            raise ExprError(f"Carácter no válido en {s!r} (posición {pos}): {s[pos:pos+10]!r}")
        num, name, op = m.groups()
        if num is not None:
            out.append(("num", num))
        elif name is not None:
            out.append(("name", name))
        else:
            out.append(("op", "^" if op == "**" else op))
        pos = m.end()
    return out


class _Parser:
    funcs = FUNCS
    consts = CONSTS

    def __init__(self, tokens, variables: Iterable[str]):
        self.t, self.i, self.vars = tokens, 0, set(variables)

    def pow(self, base, exp):
        return f"np.power({base},{exp})"

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else (None, None)

    def eat(self, val=None):
        tok = self.peek()
        if tok[0] is None or (val is not None and tok[1] != val):
            raise ExprError(f"Se esperaba {val!r} y se encontró {tok[1]!r}")
        self.i += 1
        return tok

    def expr(self):
        left = self.term()
        while self.peek()[1] in ("+", "-"):
            op = self.eat()[1]
            left = f"({left}{op}{self.term()})"
        return left

    def term(self):
        left = self.unary()
        while self.peek()[1] in ("*", "/"):
            op = self.eat()[1]
            left = f"({left}{op}{self.unary()})"
        return left

    def unary(self):
        if self.peek()[1] in ("-", "+"):
            op = self.eat()[1]
            return f"({op}{self.unary()})"
        return self.power()

    def power(self):
        base = self.atom()
        if self.peek()[1] == "^":
            self.eat()
            return self.pow(base, self.unary())
        return base

    def atom(self):
        kind, val = self.peek()
        if kind == "num":
            self.eat()
            return f"({val})"
        if kind == "name":
            self.eat()
            name = ALIASES.get(val, val)
            if self.peek()[1] == "(":
                if name not in self.funcs:
                    raise ExprError(f"Función desconocida: {val}")
                self.eat("(")
                args = []
                if self.peek()[1] != ")":
                    args.append(self.expr())
                    while self.peek()[1] == ",":
                        self.eat(",")
                        args.append(self.expr())
                self.eat(")")
                return f"{self.funcs[name]}({','.join(args)})"
            if val in self.vars:
                return f"v_{val}"
            if val in self.consts:
                return self.consts[val]
            raise ExprError(f"Variable desconocida: {val!r} (variables válidas: {sorted(self.vars)})")
        if val == "(":
            self.eat("(")
            inner = self.expr()
            self.eat(")")
            return f"({inner})"
        raise ExprError(f"Expresión incompleta cerca de {val!r}")


_NS = {"np": np, "_sec": _sec, "_csc": _csc, "_cot": _cot, "_sel": _sel, "__builtins__": {}}


class Expr:
    """Expresión compilada. ``Expr("x^2+C", ["x", "C"])(x=arr, C=2)``."""

    def __init__(self, text: str | float | int, variables: Sequence[str]):
        self.text = str(text)
        self.variables = list(variables)
        parser = _Parser(_tokenize(self.text), self.variables)
        code = parser.expr()
        if parser.i != len(parser.t):
            raise ExprError(f"Sobran símbolos en {self.text!r}")
        self.code = code
        args = ",".join(f"v_{v}" for v in self.variables)
        self._fn: Callable = eval(f"lambda {args}: {code}", _NS)  # noqa: S307 (código generado, tokens validados)

    def __call__(self, **env):
        vals = [np.asarray(env[v], dtype=float) if v in env else np.float64(np.nan) for v in self.variables]
        with np.errstate(all="ignore"):
            return self._fn(*vals)

    def __repr__(self):
        return f"Expr({self.text!r})"


def compile_expr(text, variables: Sequence[str]) -> Expr:
    """Compila ``text`` como función de ``variables`` (lista de nombres)."""
    return Expr(text, variables)


def free_names(text: str) -> set[str]:
    """Nombres (no funciones ni constantes) que aparecen en una expresión."""
    out = set()
    toks = _tokenize(text)
    for i, (k, v) in enumerate(toks):
        if k == "name":
            nxt = toks[i + 1][1] if i + 1 < len(toks) else None
            if nxt == "(" or v in CONSTS:
                continue
            out.add(v)
    return out
