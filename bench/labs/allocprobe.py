"""Allocation-cost probe: isolates container/object allocation + GC tracking.

Same differential method as callprobe.py: subtract the bare loop cost.
"""
import sys
import time

REPS = 7
N = 1_000_000


class Plain:
    pass


class WithInit:
    def __init__(self):
        self.x = 1


def b_loop(n):
    for _ in range(n):
        pass


def b_list(n):
    for _ in range(n):
        x = []


def b_tuple(n):
    for _ in range(n):
        x = (1, 2)


def b_dict(n):
    for _ in range(n):
        x = {}


def b_set(n):
    for _ in range(n):
        x = set()


def b_float(n):
    for _ in range(n):
        x = 1.5 + 1


def b_bigint(n):
    for _ in range(n):
        x = 100000 * 2


def b_append(n):
    a = []
    for i in range(n):
        a.append(i)


def b_raise(n):
    for _ in range(n):
        try:
            raise ValueError("x")
        except ValueError:
            pass


def b_plain_inst(n):
    for _ in range(n):
        Plain()


def b_init_inst(n):
    for _ in range(n):
        WithInit()


def b_closure(n):
    def outer():
        v = 1

        def inner():
            return v

        return inner
    for _ in range(n):
        outer()


CASES = [
    ("loop only", b_loop),
    ("list []", b_list),
    ("tuple (1,2)", b_tuple),
    ("dict {}", b_dict),
    ("set()", b_set),
    ("float add", b_float),
    ("bigint mul", b_bigint),
    ("list.append loop", b_append),
    ("raise+catch", b_raise),
    ("Plain() no init", b_plain_inst),
    ("WithInit()", b_init_inst),
    ("closure create", b_closure),
]


def main():
    print(f"=== {sys.implementation.name} python {sys.version.split()[0]} ===")
    vals = {}
    for name, fn in CASES:
        best = float("inf")
        for _ in range(REPS):
            t0 = time.perf_counter()
            fn(N)
            dt = time.perf_counter() - t0
            if dt < best:
                best = dt
        vals[name] = best / N * 1e9
    base = vals["loop only"]
    for name, _ in CASES:
        print(f"{name:20s} {vals[name]:9.1f} ns   net {vals[name] - base:8.1f}")


if __name__ == "__main__":
    main()
