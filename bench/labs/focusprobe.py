"""Focused probe for regression checks: the cases that must not regress.

Small workload per run so an alternating A/B can afford many rounds.
"""
import sys
import time

N = 300_000


class C:
    def m(self, a):
        return a + 1


obj = C()
lst = list(range(1000))


def b_loop(n):
    for _ in range(n):
        pass


def b_instantiate(n):
    for _ in range(n):
        C()


def b_method(n):
    for _ in range(n):
        obj.m(3)


def b_raise(n):
    for _ in range(n):
        try:
            raise ValueError("x")
        except ValueError:
            pass


def b_index(n):
    for _ in range(n):
        x = lst[7]


def b_call(n):
    for _ in range(n):
        b_loop(0)


def gen():
    yield 1
    yield 2


def b_gen(n):
    for _ in range(n):
        g = gen()
        next(g)
        next(g)


CASES = [
    ("loop only", b_loop),
    ("class instantiate", b_instantiate),
    ("method call", b_method),
    ("raise+catch", b_raise),
    ("list index", b_index),
    ("function call", b_call),
    ("generator next", b_gen),
]


def main():
    print(f"=== {sys.implementation.name} ===")
    for name, fn in CASES:
        best = float("inf")
        for _ in range(5):
            t0 = time.perf_counter()
            fn(N)
            dt = time.perf_counter() - t0
            if dt < best:
                best = dt
        print(f"{name:22s} {best / N * 1e9:9.1f} ns")


if __name__ == "__main__":
    main()
