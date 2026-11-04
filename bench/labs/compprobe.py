"""Where does the list-comprehension case's time go?

`bench.py`'s comprehension case is `[i * i for i in range(100)]` and sits at 0.44
of CPython's throughput. These shapes differ by exactly one mechanism each, so
the deltas attribute the gap: a bare comprehension versus the multiplying one, the
same product accumulated without a list, the same loop appending by hand (which
adds a LOAD_METHOD/attribute lookup the comprehension does not pay), and a
comprehension over a pre-built list (which removes the range iterator).

    python bench/labs/compprobe.py [reps]
"""

import sys
import time

ITER = 2_000
REPS = int(sys.argv[1]) if len(sys.argv) > 1 else 7


def comp_mul(n):
    for _ in range(n):
        [i * i for i in range(100)]


def comp_bare(n):
    for _ in range(n):
        [i for i in range(100)]


def comp_over_list(n):
    data = list(range(100))
    for _ in range(n):
        [i * i for i in data]


def no_list(n):
    for _ in range(n):
        s = 0
        for i in range(100):
            s += i * i


def manual_append(n):
    for _ in range(n):
        out = []
        append = out.append
        for i in range(100):
            append(i * i)


def list_call(n):
    for _ in range(n):
        list(range(100))


def timeit(fn):
    best = None
    for _ in range(REPS):
        started = time.perf_counter()
        fn(ITER)
        elapsed = time.perf_counter() - started
        if best is None or elapsed < best:
            best = elapsed
    return 1e9 * best / ITER


for name, fn in (
    ("comp_mul", comp_mul),
    ("comp_bare", comp_bare),
    ("comp_over_list", comp_over_list),
    ("list(range(100))", list_call),
    ("no_list s+=i*i", no_list),
    ("manual_append", manual_append),
):
    print(f"{name:20s} {timeit(fn):10.1f} ns")
