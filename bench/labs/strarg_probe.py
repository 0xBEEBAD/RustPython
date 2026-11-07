"""Does a builtin str method get more expensive per argument?

Task #33 says native calls that miss a specialized kernel still build an
argument `Vec`. bench.py's string ops row now spends ~172 ns in the call
machinery around `split`, against ~90 ns for the whole `s.upper()` op, so the
question is how much of that difference is the arguments themselves. Same loop
shape as `strops_split.py`, so subtracting this file's own control row leaves
the operation.

    rustpython bench/labs/strarg_probe.py
    python     bench/labs/strarg_probe.py

Measured on rp-lite-114 against cp314 with that run's own control subtracted
(RP 49.2 ns, CP 13.9 - the machine was busy, so read the deltas, not the
absolute values):

    row                          RP net   CP net
    s.upper()            [0 arg]    92.9     21.1
    s.isascii()          [0 arg]    84.2      7.0
    s.startswith('abc')  [1 arg]    51.0     15.5
    s.count('a')         [1 arg]   138.8     20.8
    s.split('d')  sep present        282.5     73.0
    s.startswith('abc',0)   +isize  144.8     21.0
    s.split('z',-1)         +isize  238.0     43.4
    s.split('z',1e12)    +bigint    317.4     49.3
    ident(1)  python func         108.3     14.5

CPython charges ~5.5 ns for one more integer argument; we charge 44-94. Note
that `startswith('abc')` at 51.0 net is cheaper than `upper()` at 92.9, so this
is not a monotone "args cost money" story - the per-method route matters more,
and these rows are the starting point for telling them apart.
"""
import sys
import time

N = 200_000
REPEAT = 5


def control(n):
    s = "abcdefgh"
    for _ in range(n):
        t = s


def zero_args(n):
    s = "abcdefgh"
    for _ in range(n):
        t = s.upper()


def one_arg(n):
    s = "abcdefgh"
    for _ in range(n):
        t = s.startswith("abc")


def two_args(n):
    s = "abcdefgh"
    for _ in range(n):
        t = s.startswith("abc", 0)


def three_args(n):
    s = "abcdefgh"
    for _ in range(n):
        t = s.startswith("abc", 0, 8)


def one_keyword(n):
    s = "abcdefgh"
    for _ in range(n):
        t = s.count("a")


def two_positional_str(n):
    s = "abcdefgh"
    for _ in range(n):
        t = s.split("d")


def zero_args_bool(n):
    s = "abcdefgh"
    for _ in range(n):
        t = s.isascii()


def pyfunc_one_arg(fn, n):
    for _ in range(n):
        t = fn(1)


def ident(x):
    return x


CASES = [
    ("control: loop+store", control, None),
    ("s.upper()  [0 args]", zero_args, None),
    ("s.startswith('abc') [1]", one_arg, None),
    ("s.startswith('abc',0) [2]", two_args, None),
    ("s.startswith('abc',0,8) [3]", three_args, None),
    ("s.count('a') [1, scans]", one_keyword, None),
    ("s.split('d') [1, present]", two_positional_str, None),
    ("s.isascii() [0 args, bool]", zero_args_bool, None),
    ("py ident(1) [1 arg]", pyfunc_one_arg, ident),
]

print("=== %s py%s ===" % (sys.implementation.name, sys.version.split()[0]))
for name, fn, extra in CASES:
    best = None
    for _ in range(REPEAT):
        t0 = time.perf_counter()
        if extra is None:
            fn(N)
        else:
            fn(extra, N)
        dt = time.perf_counter() - t0
        if best is None or dt < best:
            best = dt
    ns = best / N * 1e9
    print("%-30s %9.3f M ops/s %9.1f ns/op" % (name, 1e3 / ns, ns))
