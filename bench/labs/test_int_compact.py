"""Every value a small-int fast path has to get right.

`compact_i64` reads a `BigInt` that occupies one base-2^32 digit without running
the generic conversion, and `int_fast_op` only uses it when the result still fits
`i64`; anything wider falls through to the general operation. So the boundaries
that matter are the digit count and the i64 overflow, on both sides of zero, for
the three operators that go through that helper - plus the cases that must never
reach it at all (a subclass, a bool, a float, a huge operand).

Run on both interpreters and diff:

    python bench/labs/test_int_compact.py
"""

import sys

VALUES = [
    0,
    1,
    -1,
    5,
    -5,
    255,
    256,
    257,
    2**30 - 1,
    2**30,
    2**31 - 1,
    -(2**31),
    2**32 - 1,
    -(2**32 - 1),
    2**32,
    2**32 + 1,
    -(2**32),
    2**33,
    2**62,
    -(2**62),
    2**63,
    -(2**63),
    2**64,
    2**100 + 7,
    -(2**100),
]


class Sub(int):
    pass


print(f"-- add {len(VALUES) ** 2} pairs")
for a in VALUES:
    row = []
    for b in VALUES:
        row.append(repr(a + b))
    print("|".join(row))

print("-- sub")
for a in VALUES:
    print("|".join(repr(a - b) for b in VALUES))

print("-- mul")
for a in VALUES:
    print("|".join(repr(a * b) for b in VALUES))

print("-- floordiv/mod, incl. zero divisor")
for a in VALUES:
    row = []
    for b in VALUES + [0]:
        try:
            row.append(f"{a // b}/{a % b}")
        except ZeroDivisionError:
            row.append("ZeroDivisionError")
    print("|".join(row))

print("-- in-place ops")
for a in VALUES[:12]:
    for b in VALUES[:12]:
        x = a
        x += b
        y = a
        y *= b
        z = a
        z -= b
        print(f"{x}|{y}|{z}")

print("-- non-exact operands")
print(repr(Sub(3) + 4), repr(4 + Sub(3)), repr(Sub(3) * Sub(4)))
print(repr(True + 1), repr(1 + False), repr(True * 3))
print(repr(3 + 1.5), repr(1.5 * 2), repr(2**70 + 0.5))
print(repr(-(-2**70)), repr(+(-(2**70))), repr(abs(-(2**70))))
print(repr((2**64).bit_length()), repr(int(-1) if False else 1))
print("-- bitwise and shifts (the compactlongs paths)")
SMALL = [0, 1, -1, 255, 256, 2**30 - 1, 2**30, 2**31, 2**32, 2**33 + 7, -(2**32), 2**63, -(2**63)]
for a in SMALL:
    row = []
    for b in SMALL:
        sh = min(abs(b), 70)
        row.append(f"{a & b:x}/{a | b:x}/{a ^ b:x}/{a << sh:x}/{a >> sh:x}")
    print("|".join(row))

print("-- shift errors")
for expr in ["1 << -1", "(2**70) >> -1", "1 << 2**70", "(2**70) << 2**70"]:
    try:
        value = eval(expr)
    except Exception as exc:
        print(f"{expr:18s} {type(exc).__name__}: {exc}")
    else:
        print(f"{expr:18s} ok bits={value.bit_length()}")

print("-- slicing with int bounds (the slice-bound and subscript fast paths)")
data = list(range(40))
for a in [None, 0, 1, -1, 5, -5, 39, 40, 41, -41, 2**31, -(2**31), 2**70, -(2**70)]:
    try:
        step = f"{data[::a] if a is not None else data}"
    except ValueError as exc:
        step = f"ValueError: {exc}"
    print(f"{data[a:]}|{data[:a]}|{step}")

print("-- dict/list/tuple index by the same values")
pairs = {i: i for i in range(40)}
for a in [0, 1, -1, 39, 40, -40, 2**31, -(2**31), 2**70, 1.0, True]:
    try:
        shown = repr((pairs[a], data[a], tuple(data)[a]))
    except Exception as exc:
        shown = f"{type(exc).__name__}: {exc}"
    print(f"{a!r:14s} {shown}")

print("-- sum over a range (the shape that pays for this)")
print(repr(sum(i * i for i in range(200))))
print(repr(sum(i * 2 - 1 for i in range(2000))))
print(f"{'implementation':22s} {sys.implementation.name} {sys.version_info[:3]}")
