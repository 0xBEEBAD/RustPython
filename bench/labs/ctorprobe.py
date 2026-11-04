"""Cost of class-form calls: builtin exceptions, user classes, plain functions."""
import sys
import time

N = 1_000_000
REPS = 7


class C:
    pass


class E1(Exception):
    pass


def b_loop(n):
    for _ in range(n):
        pass


def b_valuerror_arg(n):
    for _ in range(n):
        x = ValueError(1)


def b_valuerror_bare(n):
    for _ in range(n):
        x = ValueError()


def b_heapexc_arg(n):
    for _ in range(n):
        x = E1("x")


def b_class(n):
    for _ in range(n):
        x = C()


def b_func(n):
    for _ in range(n):
        x = noop(1)


def b_int(n):
    for _ in range(n):
        x = int(1)


def noop(a):
    return a


CASES = [
    ("loop floor", b_loop),
    ("ValueError(1)", b_valuerror_arg),
    ("ValueError()", b_valuerror_bare),
    ("E1('x') heap", b_heapexc_arg),
    ("C() user class", b_class),
    ("noop(1) func", b_func),
    ("int(1)", b_int),
]


def main():
    print("=== %s %s ===" % (sys.implementation.name, sys.version.split()[0]))
    vals = {}
    for name, fn in CASES:
        best = float("inf")
        for _ in range(REPS):
            t0 = time.perf_counter()
            fn(N)
            best = min(best, time.perf_counter() - t0)
        vals[name] = best / N * 1e9
    floor = vals["loop floor"]
    for name, _ in CASES:
        print("%-18s %9.1f ns   net %8.1f" % (name, vals[name], vals[name] - floor))


main()
