"""cg_rmpair.py - cost of ONE mortal refcount inc/dec pair inside the call path.

LUNA_ABLATE=exitclone makes the frame exit path clone the return value on every
exit (one extra incref + one extra decref of a mortal PyObjectRef per call).
Comparing default vs that ablation prices a single refcount pair in the same
code shape as the LOAD_GLOBAL owned push we want to remove.
"""
import time
import sys


def f(a, b):
    return a + b


def bench_call(n):
    for _ in range(n):
        f(1, 2)


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

tc = timeit(bench_call, n)
tf = timeit(bench_floor, n)
ns = lambda t: t / n * 1e9
print(f"{sys.implementation.name:10s} n={n:>10,}  floor={ns(tf):7.1f}  "
      f"call={ns(tc):7.1f}  call-floor={ns(tc)-ns(tf):7.1f} ns")
