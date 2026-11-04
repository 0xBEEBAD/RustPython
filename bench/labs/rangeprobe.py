"""Range-loop floor shapes, timed in ns per iteration.

Used to decide whether reusing the loop int actually engages: the same
executable is run twice, once with `LUNA_ABLATE=rangeint`, so only the reuse
decision differs.
"""
import sys
import time

N = 200_000
REPS = 5


def f(a, b):
    return a + b


def loop_named_pass():
    for i in range(N):
        pass


def loop_underscore_pass():
    for _ in range(N):
        pass


def loop_named_body():
    x = 0
    for i in range(N):
        x = i


def loop_call():
    for _ in range(N):
        f(1, 2)


def loop_arith():
    s = 0
    for i in range(N):
        s += i


def loop_small():
    for _ in range(N // 200):
        for i in range(200):
            pass


# Iterators, not steps: each outer iteration builds a fresh range_iterator, so
# the number below is *outer* iterations and one malloc can show up in ns/iter.
def nested_inner8():
    for _ in range(N // 8):
        for _ in range(8):
            pass


def nested_inner2():
    for _ in range(N // 2):
        for _ in range(2):
            pass


CASES = [
    ("named_pass", loop_named_pass, N),
    ("underscore_pass", loop_underscore_pass, N),
    ("named_store", loop_named_body, N),
    ("call", loop_call, N),
    ("arith", loop_arith, N),
    ("small_pooled", loop_small, N),
    ("nested_x8", nested_inner8, N // 8),
    ("nested_x2", nested_inner2, N // 2),
]


def time_case(fn, iters):
    fn()
    best = None
    for _ in range(REPS):
        t0 = time.perf_counter()
        fn()
        dt = time.perf_counter() - t0
        best = dt if best is None else min(best, dt)
    return best


for name, fn, iters in CASES:
    ns = time_case(fn, iters) / iters * 1e9
    print(f"{name:18s} {ns:8.1f} ns/iter")
