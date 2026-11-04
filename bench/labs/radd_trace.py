"""Does the right operand's __radd__ get its chance, for every sequence shape?

CPython's `PyNumber_Add` consults the reflected slot before the left type's
`sq_concat` can refuse, so `__radd__` is called for exact list, list subclass,
exact tuple and tuple subclass alike. RustPython's builtin sequences answer
`__add__` from the concat slot, which raises - so the subclass rows are the
ones that differ (task #79).

    python bench/labs/radd_trace.py
"""


class Marker:
    def __radd__(self, other):
        print(f"  __radd__ called for {type(other).__name__}")
        return "reflected"


class StrictMarker:
    """Declines, so the left type's own refusal must surface."""

    def __radd__(self, other):
        return NotImplemented


class ListSub(list):
    pass


class TupleSub(tuple):
    pass


CASES = [
    ("[1] + Marker()", lambda: [1] + Marker()),
    ("ListSub + Marker()", lambda: ListSub([1]) + Marker()),
    ("(1,) + Marker()", lambda: (1,) + Marker()),
    ("TupleSub + Marker()", lambda: TupleSub((1,)) + Marker()),
    ("b'a' + Marker()", lambda: b"a" + Marker()),
    ("bytearray + Marker()", lambda: bytearray(b"a") + Marker()),
    ("'a' + Marker()", lambda: "a" + Marker()),
    ("[1] + StrictMarker()", lambda: [1] + StrictMarker()),
    ("ListSub + StrictMarker()", lambda: ListSub([1]) + StrictMarker()),
    ("list.__add__(ListSub, Marker)", lambda: list.__add__(ListSub([1]), Marker())),
    ("list.__add__([1], StrictMarker)", lambda: list.__add__([1], StrictMarker())),
    ("tuple.__add__(TupleSub, Marker)", lambda: tuple.__add__(TupleSub((1,)), Marker())),
]

for label, fn in CASES:
    try:
        print(f"{label:32s} ok {fn()!r}")
    except Exception as exc:
        print(f"{label:32s} {type(exc).__name__}: {exc}")

print(f"{'implementation':32s} {__import__('sys').implementation.name}")
