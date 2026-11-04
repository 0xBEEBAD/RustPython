"""Per-STORE_FAST cost, measured as the slope over functions that store k locals.

`x = a = ...` compiles to one LOAD_CONST plus k STORE_FASTs, so the difference
between k=1 and k=8 divided by seven is the cost of one store, with the call and
the loop floor cancelling out.
"""

import sys
import time

N = 200_000
REPS = 5


def zzstore1():
    a1 = 1


def zzstore2():
    a1 = a2 = 1


def zzstore4():
    a1 = a2 = a3 = a4 = 1


def zzstore8():
    a1 = a2 = a3 = a4 = a5 = a6 = a7 = a8 = 1


def zzload8():
    a1 = a2 = a3 = a4 = a5 = a6 = a7 = a8 = 1
    return a1 + a2 + a3 + a4 + a5 + a6 + a7 + a8


CASES = [
    ("store1", zzstore1),
    ("store2", zzstore2),
    ("store4", zzstore4),
    ("store8", zzstore8),
    ("load8", zzload8),
]

print("==", sys.version.split()[0], sys.implementation.name)
for label, fn in CASES:
    fn()
    best = None
    for _ in range(REPS):
        t0 = time.perf_counter()
        for _ in range(N):
            fn()
        dt = time.perf_counter() - t0
        ns = dt * 1e9 / N
        best = ns if best is None or ns < best else best
    print(f"{label:12s} {best:8.1f} ns/iter")
