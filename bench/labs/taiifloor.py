"""Price one loop iteration whose tail discards a call.

The POP_TOP + JUMP_BACKWARD fusion folds that pair into one dispatch, so this
probe runs exactly that shape and reports ns per iteration. `tail` is the fused
shape, `store_tail` is a control whose tail is a STORE_FAST (never fused), and
`nop_tail` is a control with no POP_TOP at all.

    python bench/labs/taiifloor.py [reps]
"""

import time

ITER = 200_000
REPS = int(__import__("sys").argv[1]) if len(__import__("sys").argv) > 1 else 7


def zztail(calls, n):
    i = 0
    while i < n:
        i += 1
        calls.append(1)
    return i


def zzstore_tail(calls, n):
    i = 0
    while i < n:
        i += 1
        last = i
    return last


def zzno_pop(calls, n):
    total = 0
    for i in range(n):
        total += i
    return total


def timeit(fn):
    calls = []
    best = None
    for _ in range(REPS):
        started = time.perf_counter()
        fn(calls, ITER)
        elapsed = time.perf_counter() - started
        if best is None or elapsed < best:
            best = elapsed
    return 1e9 * best / ITER


for name, fn in (
    ("tail_pop_call", zztail),
    ("tail_store", zzstore_tail),
    ("tail_augassign", zzno_pop),
):
    print(f"{name:16s} {timeit(fn):6.2f} ns/iter")
