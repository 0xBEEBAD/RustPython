"""Marginal allocation cost probe.

Every case is the same `for i in range(n)` loop with a different body, so
subtracting the paired case isolates exactly one operation:

  store_only        -> loop + FOR_ITER/STORE_FAST fusion, zero allocation
  int_add           -> store_only + exactly one PyInt allocation (result > 256)
  tuple2            -> store_only + one fixed-size tuple allocation
  list1             -> store_only + one list allocation + one int allocation
  str_concat        -> store_only + one str allocation (from a 2-char literal + i)

int_add - store_only is therefore the marginal cost of allocating, initializing
and freeing one small object, which is the component the interpreter floor is
made of. Run under ab.ps1 so both interpreters are pinned and alternating.
"""
import sys
import time

REPS = 7
N = 2_000_000
RANGE = range(N)


def store_only(n=N):
    for i in RANGE:
        x = i
    return x


def int_add(n=N):
    for i in RANGE:
        x = i + 100000
    return x


def tuple2(n=N):
    for i in RANGE:
        x = (i, i)
    return x


def list1(n=N):
    for i in RANGE:
        x = [i]
    return x


def str_concat(n=N):
    for i in RANGE:
        x = "ab" + str(i)
    return x


CASES = [
    ("store only (no alloc)", store_only),
    ("+ one int alloc", int_add),
    ("+ one tuple(2) alloc", tuple2),
    ("+ one list alloc", list1),
    ("+ one str alloc", str_concat),
]


def main():
    # Warm the code objects so no case pays first-run compile cost.
    for _, fn in CASES:
        fn(1000)
    print(f"=== {sys.executable.split(chr(92))[-1]} {sys.version.split()[0]} ===")
    for name, fn in CASES:
        best = None
        for _ in range(REPS):
            t0 = time.perf_counter_ns()
            fn()
            dt = (time.perf_counter_ns() - t0) // N
            best = dt if best is None or dt < best else best
        print(f"{name:<22} {best:>7.1f} ns")


main()
