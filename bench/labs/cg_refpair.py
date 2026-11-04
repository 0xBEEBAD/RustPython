"""cg_refpair.py - isolate the LOAD_GLOBAL owned-push refcount pair.

A: f(1)        -> LOAD_GLOBAL_MODULE/BUILTIN hit path (owned PyObjectRef push)
B: lf = f; lf(1) -> LOAD_FAST_BORROW hit path (borrowed push, no refcount)

Both end in the same CallPyExactArgs arm, so A-B is the load-path delta,
which is claimed to be the atomic incref/decref pair.
"""
import time
import sys


def f(a):
    return a


def loop_global(n):
    i = 0
    while i < n:
        f(1)
        i += 1


def loop_local(n):
    lf = f
    i = 0
    while i < n:
        lf(1)
        i += 1


def loop_local_bare(n):
    # loop floor only: same while-shape, no call at all
    i = 0
    while i < n:
        i += 1


def timeit(fn, n):
    best = 1e9
    for _ in range(5):
        t0 = time.perf_counter()
        fn(n)
        dt = time.perf_counter() - t0
        best = min(best, dt)
    return best


# calibrate
n = 100_000
while True:
    if timeit(loop_local_bare, n) > 0.05 or n >= 20_000_000:
        break
    n *= 4

tg = timeit(loop_global, n)
tl = timeit(loop_local, n)
tb = timeit(loop_local_bare, n)
per = lambda t: t / n * 1e9

print(f"impl={sys.implementation.name} n={n:,}")
print(f"loop floor            {per(tb):8.1f} ns/iter")
print(f"global call  A        {per(tg):8.1f} ns/iter")
print(f"local  call  B        {per(tl):8.1f} ns/iter")
print(f"A - B (load-path delta) {(per(tg)-per(tl)):8.1f} ns")
print(f"B - floor (call cost)   {(per(tl)-per(tb)):8.1f} ns")
print(f"A - floor (total)       {(per(tg)-per(tb)):8.1f} ns")
