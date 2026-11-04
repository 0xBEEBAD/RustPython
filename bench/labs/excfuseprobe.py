"""Except-clause shapes, timed in ns per iteration, for `LUNA_ABLATE=excfuse`.

The unit under test answers an identical-class clause with one pointer compare and
decides the clause branch without materializing the match bool. These shapes hit
each path in turn, plus a floor case that contains no clause at all - if the floor
moves, the run is noise, not effect.
"""
import sys
import time

N = 300_000
REPS = 5


class E1(Exception):
    pass


class Other(Exception):
    pass


def make_multi(k):
    """raise E1(); k clauses, none of which match - the worst case for scanning."""
    src = "def f(n):\n    for _ in range(n):\n        try:\n            raise E1('x')\n"
    for i in range(k):
        src += "        except C%d:\n            pass\n" % i
    src += "        except BaseException:\n            pass\n"
    ns = {"E1": E1}
    for i in range(k):
        ns["C%d" % i] = type("C%d" % i, (Exception,), {})
    exec(src, ns)
    return ns["f"]


def identity_clause(n):
    for _ in range(n):
        try:
            raise E1("x")
        except E1:
            pass


def mro_clause(n):
    # The target is a base class, so the identity answer does not apply.
    for _ in range(n):
        try:
            raise E1("x")
        except BaseException:
            pass


def tuple_clause(n):
    for _ in range(n):
        try:
            raise E1("x")
        except (Other, E1):
            pass


def no_match_clause(n):
    # Every clause is tested and rejected; the branch is taken.
    for _ in range(n):
        try:
            raise E1("x")
        except Other:
            pass
        except BaseException:
            pass


def construct_only(n):
    for _ in range(n):
        E1("x")


def floor_loop(n):
    for _ in range(n):
        pass


CASES = [
    ("identity", identity_clause),
    ("mro", mro_clause),
    ("tuple", tuple_clause),
    ("nomatch", no_match_clause),
    ("clauses8", make_multi(8)),
    ("ctor", construct_only),
    ("floor", floor_loop),
]


def time_case(fn, iters):
    fn(1000)
    best = None
    for _ in range(REPS):
        t0 = time.perf_counter()
        fn(iters)
        dt = time.perf_counter() - t0
        best = dt if best is None else min(best, dt)
    return best


for name, fn in CASES:
    ns = time_case(fn, N) / N * 1e9
    print(f"{name:12s} {ns:8.1f} ns/iter")
