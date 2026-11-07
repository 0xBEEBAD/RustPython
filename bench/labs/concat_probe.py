"""Price `str + str` as a function of the result length.

bench.py's string ops case does `"abcdefgh".upper() + "ij"`, a 10-byte result,
and that one `+` costs 73.4 ns net against CPython's 24.7. `StrData` can hold
22 bytes inside the header with no heap buffer at all, so the question this
answers is whether the cost is the temporary buffer the add path builds
(`Wtf8Buf`, always) rather than the bytes it copies.

Rows below are ordered by result length; the 22-byte boundary is where SSO
stops, so a step at that boundary says the allocation is the cost and a flat
line says the fixed machinery is.

    rustpython bench/labs/concat_probe.py
    python     bench/labs/concat_probe.py

Measured on rp-lite-114 against cp314, each side minus its own control (RP 32.7,
CP 15.7):

    result bytes    RP net   CP net
    8                 55.8     21.4
    10                58.0     21.2
    22 (SSO limit)    53.6     21.7
    23 (past it)      52.6     21.6
    40                60.1     23.7
    100               73.2     23.8
    c += b inplace    58.9     29.9

What this kills: `StrData` holds 22 bytes inline and the cost does not change
between 22 and 23 bytes, i.e. crossing from inline storage to a boxed buffer
buys nothing measurable here. So the ~55 ns is fixed machinery, not the
allocation, and "concatenate ASCII into one allocation instead of a Wtf8Buf
temporary" was dropped on the strength of this table rather than built and
measured. The remaining shape of the gap is 55 ns fixed against CPython's 21.
"""
import sys
import time

N = 200_000
REPEAT = 5


def control(n):
    a = "abcdefgh"
    b = "ij"
    for _ in range(n):
        c = a


def add(len_a, len_b, n):
    a = "a" * len_a
    b = "b" * len_b
    for _ in range(n):
        c = a + b


def make(len_a, len_b):
    def fn(n, len_a=len_a, len_b=len_b):
        add(len_a, len_b, n)

    return fn


CASES = [
    ("control", control),
    ("4+4 = 8", make(4, 4)),
    ("8+2 = 10", make(8, 2)),
    ("11+11 = 22", make(11, 11)),
    ("11+12 = 23", make(11, 12)),
    ("20+20 = 40", make(20, 20)),
    ("50+50 = 100", make(50, 50)),
    ("8+2 inplace", None),
]


def inplace(n):
    a = "abcdefgh"
    b = "ij"
    for _ in range(n):
        c = "abcdefgh"
        c += b


print("=== %s py%s ===" % (sys.implementation.name, sys.version.split()[0]))
rows = [(name, fn) for name, fn in CASES if fn is not None] + [("c += b (inplace)", inplace)]
for name, fn in rows:
    best = None
    for _ in range(REPEAT):
        t0 = time.perf_counter()
        fn(N)
        dt = time.perf_counter() - t0
        if best is None or dt < best:
            best = dt
    ns = best / N * 1e9
    print("%-18s %9.3f M ops/s %9.1f ns/op" % (name, 1e3 / ns, ns))
