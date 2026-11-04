"""The concatenation error family, one line per shape.

CPython produces these messages in the type's own `nb_add`/`sq_concat` slot
(`unicode_concat`, `bytes_concat`, `list_concat`), so each type owns its wording,
while the generic `unsupported operand type(s)` comes from the shared binary-op
fallback. The probe therefore walks str/bytes/bytearray/list/tuple/range against
int/str/bytes/list/None/subclass operands, in both orders, for `+` and `+=`.

Run on both interpreters and diff:

    python bench/labs/test_concat_messages.py
"""

import sys


class IntSub(int):
    pass


class StrSub(str):
    pass


class ListSub(list):
    pass


class MyInt:
    def __radd__(self, other):
        return "reflected"


def show(expr):
    try:
        value = eval(expr, globals())
    except Exception as exc:
        print(f"{expr:34s} {type(exc).__name__}: {exc}")
    else:
        print(f"{expr:34s} ok {value!r}")


def iadd(left, right):
    try:
        target = eval(left, globals())
        target += eval(right, globals())
    except Exception as exc:
        print(f"{left} += {right:22s} {type(exc).__name__}: {exc}")
    else:
        print(f"{left} += {right:22s} ok {target!r}")


RIGHTS = ["1", "1.5", "'s'", "b'b'", "bytearray(b'c')", "[2]", "(2,)", "None", "()", "IntSub(3)", "StrSub('t')", "MyInt()"]
LEFTS = ["'a'", 'b"a"', "bytearray(b'a')", "[1]", "(1,)", "range(3)", "StrSub('a')", "ListSub([1])", "IntSub(1)", "1", "1.5", "{1: 2}", "{1}", "frozenset({1})", "'a'.join"]

for left in LEFTS:
    for right in RIGHTS:
        if left.endswith(".join"):
            continue
        show(f"{left} + {right}")

for left in ["'a'", 'b"a"', "bytearray(b'a')", "[1]", "(1,)", "StrSub('a')", "ListSub([1])"]:
    for right in ["1", "'s'", "b'b'", "[2]", "None"]:
        iadd(left, right)

show('"a".join([1, 2])')
show('"a".join(1)')
show("b'a'.join([b'x', 2])")
show("[1] * 'x'")
show("'x' * 'y'")
show("(1,) * 'x'")
show("bytearray(b'a') * 'x'")
print(f"{'implementation':34s} {sys.implementation.name} {sys.version_info[:3]}")

# The same slots reached as methods: CPython raises from these rather than
# handing back NotImplemented, because for list/bytes/tuple the method *is* the
# sq_concat wrapper.
for expr in ["list.__add__([1], 2)", "tuple.__add__((1,), 2)", "bytes.__add__(b'a', 1)",
             "bytearray.__add__(bytearray(b'a'), 1)", "str.__add__('a', 1)",
             "list.__add__(ListSub([1]), MyInt())", "bytes.__add__(b'a', MyInt())",
             "bytearray.__iadd__(bytearray(b'a'), MyInt())", "[1] + MyInt()",
             "ListSub([1]) + MyInt()", "b'a' + MyInt()", "bytearray(b'a') + MyInt()",
             "b'a'.join([b'x', memoryview(b'y')])", "'a'.join(StrSub('bc'))",
             "b'a'.join([b'x', StrSub('y')])", "'a'.join(['x', StrSub('y')])"]:
    show(expr)

# join and repeat wordings, plus the identity CPython keeps for a one-element
# join of an exact str handed to a non-list iterable.
for expr in ["'a'.join([b'x'])", "bytearray(b'a').join(1)", "b'a'.join(None)",
             "'a'.join(iter([]))", "'a'.join(iter(['a','b']))", "'a'.join([1, 2, 3])",
             "b'a'.join([b'x', [1]])", "'a'.join(('x', 1))", "'a'.join(StrSub('b'))",
             "[1] * IntSub(3)", "'x' * None", "b'x' * 'y'", "(1,) * None",
             "list.__mul__([1], 'x')", "'a' * 0", "[1] * -1", "b'a' * True"]:
    show(expr)


def imul(left, right):
    try:
        target = eval(left, globals())
        target *= eval(right, globals())
    except Exception as exc:
        print(f"{left} *= {right:22s} {type(exc).__name__}: {exc}")
    else:
        print(f"{left} *= {right:22s} ok {target!r}")


for left, right in [("[1]", "'x'"), ("bytearray(b'a')", "'x'"), ("[1]", "None"),
                    ("bytearray(b'a')", "1.5")]:
    imul(left, right)

_one = 'a'
print(f"{'single exact str via generator':34s} {''.join(y for y in (_one,)) is _one}")
print(f"{'single exact str via map':34s} {','.join(map(str, [7]))!r}")
print(f"{'sep is subclass':34s} {StrSub('-').join(['a', 'b'])!r}")
