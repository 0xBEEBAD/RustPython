"""Raise-chain accounting probe: reproduce bench.py's `raise/catch exc` row and
decompose it into the stages the chain is built from, all in one process so the
rows share one code layout.

    rp-lite-119.exe bench/labs/rp_exc_chain.py
    cp314/python.exe bench/labs/rp_exc_chain.py

Rows are ops/s as well as ns/op so they can be read straight against
bench.py's `raise/catch exc` number.
"""
import sys
import time

N = 100_000
REPEATS = 7


def throw(i):
    raise ValueError(i)


def plain(i):
    return i


def row_across_call(n):
    """bench.py's shape: raise inside a callee, handler in the caller."""
    caught = 0
    for i in range(n):
        try:
            throw(i)
        except ValueError:
            caught += 1


def row_same_frame(n):
    """Same try/except, no call: one traceback entry instead of two."""
    caught = 0
    for i in range(n):
        try:
            raise ValueError(i)
        except ValueError:
            caught += 1


def row_call_only(n):
    caught = 0
    for i in range(n):
        plain(i)
        caught += 1


def row_construct_only(n):
    for i in range(n):
        ValueError(i)


def row_raise_uncaught(n):
    """One raise that reaches the top: chain build without the handler."""
    try:
        for i in range(n):
            try:
                if i == 0:
                    raise ValueError(i)
            except ValueError:
                pass
    except ValueError:
        pass


def row_tb_only(n):
    """Difference against row_across_call prices only the traceback/exception
    plumbing: same loop, exception raised and caught but with no arg tuple."""
    caught = 0
    for i in range(n):
        try:
            throw2(i)
        except ValueError:
            caught += 1


def throw2(i):
    raise ValueError


def measure(fn):
    best = None
    for _ in range(REPEATS):
        t0 = time.perf_counter()
        fn(N)
        dt = time.perf_counter() - t0
        if best is None or dt < best:
            best = dt
    return best


rows = [
    ("across_call(bench)", row_across_call),
    ("same_frame", row_same_frame),
    ("across_call_noarg", row_tb_only),
    ("call_only", row_call_only),
    ("construct_only", row_construct_only),
]

print("# %s %s" % (sys.implementation.name, ".".join(map(str, sys.version_info[:3]))))
print("%-22s %10s %10s %14s" % ("row", "ns/op", "us/100k", "ops/s"))
for name, fn in rows:
    dt = measure(fn)
    print("%-22s %10.1f %10.4f %14s" % (name, dt / N * 1e9, dt * 1e6, format(N / dt, ",.0f")))
