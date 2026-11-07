"""Ladder across the exact bench shape: loop, loop+call, loop+call inside a try
that never fires, and the raise itself. The `call_in_try` row is the zero-cost
handler setup: `across - call_in_try` is the raise-specific part with no
subtraction guesswork, and `call_in_try - call` is what our exception-table
handler entry costs when nothing is raised.

    rp-lite-119.exe bench/labs/rp_exc_ladder.py
    cp314/python.exe bench/labs/rp_exc_ladder.py
"""
import sys
import time

N = 100_000
REPEATS = 7


def throw(i):
    raise ValueError(i)


def plain(i):
    return i


def row_loop_floor(n):
    for i in range(n):
        pass


def row_call(n):
    for i in range(n):
        plain(i)


def row_call_in_try(n):
    caught = 0
    for i in range(n):
        try:
            plain(i)
        except ValueError:
            caught += 1


def row_across(n):
    caught = 0
    for i in range(n):
        try:
            throw(i)
        except ValueError:
            caught += 1


def row_same_frame(n):
    caught = 0
    for i in range(n):
        try:
            raise ValueError(i)
        except ValueError:
            caught += 1


def row_construct(n):
    for i in range(n):
        ValueError(i)


def measure(fn):
    best = None
    for _ in range(REPEATS):
        t0 = time.perf_counter()
        fn(N)
        dt = time.perf_counter() - t0
        if best is None or dt < best:
            best = dt
    return best / N * 1e9


rows = [
    ("loop_floor", row_loop_floor),
    ("call", row_call),
    ("call_in_try", row_call_in_try),
    ("same_frame", row_same_frame),
    ("construct", row_construct),
    ("across(bench)", row_across),
]

print("# %s %s" % (sys.implementation.name, ".".join(map(str, sys.version_info[:3]))))
print("%-16s %9s" % ("row", "ns/op"))
vals = {}
for name, fn in rows:
    vals[name] = measure(fn)
    print("%-16s %9.1f" % (name, vals[name]))

print("# derived")
print("raise_specific(across-call_in_try)  %9.1f" % (vals["across(bench)"] - vals["call_in_try"]))
print("try_entry(call_in_try-call)         %9.1f" % (vals["call_in_try"] - vals["call"]))
print("one_entry(same-call_in_try)         %9.1f" % (vals["same_frame"] - vals["call_in_try"]))
