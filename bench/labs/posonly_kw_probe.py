"""Positional-only vs unexpected-keyword TypeError parity.

CPython reports a positional-only collision *before* an unknown keyword, and
only when the function has no ``**kwargs`` (ceval.c
`positional_only_passed_as_keyword` is called from the ``kwdict == NULL``
branch). The names are listed in parameter order, not call order.
"""

import sys


def call(fn, *args, **kwargs):
    try:
        value = fn(*args, **kwargs)
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"
    return f"ok: {value!r}"


def call_raw(fn, args, kwargs):
    try:
        value = fn(*args, **kwargs)
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"
    return f"ok: {value!r}"


def plain(a, b, /):
    return (a, b)


def mixed(a, b, /, c, d=4):
    return (a, b, c, d)


def varkw(a, b, /, **kw):
    return kw


def posdefault(a=1, /, b=2):
    return (a, b)


def kwonly(a, /, *, b=2):
    return (a, b)


def names(a, b, /):
    return (a, b)


CASES = [
    ("only posonly", lambda: call(plain, **{"a": 1})),
    ("two posonly, call order b,a", lambda: call(names, **{"b": 1, "a": 2})),
    ("posonly then unknown", lambda: call(plain, **{"a": 1, "zz": 2})),
    ("unknown then posonly", lambda: call(plain, **{"zz": 2, "a": 1})),
    ("posonly with valid kw too", lambda: call(plain, **{"a": 1, "b": 2})),
    ("mixed posonly collision", lambda: call(mixed, 1, **{"a": 2})),
    ("mixed unknown kw", lambda: call(mixed, 1, 2, **{"e": 3})),
    ("mixed kw shadow", lambda: call(mixed, 1, 2, **{"c": 3, "b": 4})),
    ("varkw swallows posonly name", lambda: call(varkw, 1, **{"a": 2})),
    ("varkw with unknown", lambda: call(varkw, 1, 2, **{"zz": 3})),
    ("posonly default", lambda: call(posdefault, **{"a": 5})),
    ("kwonly after posonly", lambda: call(kwonly, 1, **{"a": 2})),
    ("suggest single", lambda: call(plain, **{"al": 1, "bb": 2})),
    ("suggest unknown only", lambda: call(posdefault, **{"alp": 1})),
    ("suggest two unknowns", lambda: call(mixed, 1, 2, **{"al": 3, "be": 4})),
    ("suggest close one", lambda: call(spelled, **{"alph": 1})),
    ("suggest close two", lambda: call(spelled, **{"alph": 1, "btay": 2})),
    ("non-str keyword", lambda: call_raw(plain, (), {1: 2})),
    ("non-str keyword with posonly hit", lambda: call_raw(plain, (), {1: 2, "a": 3})),
    ("too many positional", lambda: call(plain, 1, 2, 3)),
    ("method qualname", lambda: call(Outer.go, **{"x": 1})),
]


class Outer:
    def go(self, x, /):
        return x


def spelled(alpha, beta):
    return (alpha, beta)


print("==", sys.version.split()[0], sys.implementation.name)
for label, case in CASES:
    print(f"{label:32s}: {case()}")
