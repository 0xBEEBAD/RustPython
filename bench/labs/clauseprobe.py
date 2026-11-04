"""Marginal cost of one more except clause, and of the raise machinery itself."""
import sys
import time

N = 1_000_000
REPS = 5


class E1(Exception):
    pass


def make(k):
    """try: raise E1() except C0.. : pass, with the LAST clause matching E1."""
    src = "def f(n):\n    for _ in range(n):\n        try:\n            raise E1('x')\n"
    for i in range(k):
        src += "        except C%d:\n            pass\n" % i
    ns = {"E1": E1}
    for i in range(k):
        ns["C%d" % i] = E1 if i == k - 1 else type("C%d" % i, (Exception,), {})
    exec(src, ns)
    return ns["f"]


def b_ctor(n):
    for _ in range(n):
        E1("x")


def b_raise_base(n):
    for _ in range(n):
        try:
            raise E1("x")
        except BaseException:
            pass


def main():
    print("=== %s %s ===" % (sys.implementation.name, sys.version.split()[0]))

    def run(fn):
        best = float("inf")
        for _ in range(REPS):
            t0 = time.perf_counter()
            fn(N)
            best = min(best, time.perf_counter() - t0)
        return best / N * 1e9

    floor = run(b_loop_placeholder)
    ctor = run(b_ctor)
    base = run(b_raise_base)
    print("%-16s %9.1f" % ("loop floor", floor))
    print("%-16s %9.1f  net %8.1f" % ("construct", ctor, ctor - floor))
    print("%-16s %9.1f  net %8.1f" % ("raise/catch Base", base, base - floor))
    prev = None
    for k in (1, 2, 3, 4, 8):
        f = make(k)
        v = run(f) - floor
        marg = ""
        if prev is not None and k != prev[1]:
            marg = "  marginal/clause %+.1f" % ((v - prev[0]) / (k - prev[1]))
        prev = (v, k)
        print("%-16s %9.1f  net %8.1f%s" % ("%d clause(s)" % k, v + floor, v, marg))


def b_loop_placeholder(n):
    for _ in range(n):
        pass


main()
