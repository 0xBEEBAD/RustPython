"""cg_rmpair2.py - price ONE mortal refcount inc/dec pair in the call path.

`g(1,2)` returns a fresh list, which is mortal, so the LUNA_ABLATE=exitclone
extra clone/drop on frame exit is a real atomic read-modify-write pair.
default -> one pair per call;  exitclone -> two pairs per call.
The delta prices a single mortal incref+decref pair, which is exactly what the
LOAD_GLOBAL owned push costs and what a borrow would remove.
"""
import time
import sys


def g(a, b):
    return [a, b]


def sink(x):
    return x


def bench_mortal(n):
    for _ in range(n):
        sink(g(1, 2))


def bench_floor(n):
    for _ in range(n):
        pass


def timeit(fn, n):
    best = 1e9
    for _ in range(7):
        t0 = time.perf_counter()
        fn(n)
        dt = time.perf_counter() - t0
        best = min(best, dt)
    return best


n = 200_000
while True:
    if timeit(bench_floor, n) > 0.08 or n >= 50_000_000:
        break
    n *= 4

tm = timeit(bench_mortal, n)
tf = timeit(bench_floor, n)
ns = lambda t: t / n * 1e9
print(f"{sys.implementation.name:10s} n={n:>10,}  floor={ns(tf):7.1f}  "
      f"mortal-call={ns(tm):7.1f}  delta={ns(tm)-ns(tf):7.1f} ns")
