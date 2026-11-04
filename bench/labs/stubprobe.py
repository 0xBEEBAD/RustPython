"""Where does a Python call's per-call cost actually live?

The fork's calls net ~150-190 ns over CPython's for the same shape, and the
argument-binding route is now measurable on its own (LUNA_ABLATE=kwfast). What is
still unsplit is the callee: dispatch + argument binding + frame entry/exit versus
the body's own instructions.

Run this twice on the same binary, with and without LUNA_STUB_BODY=zstub. The
stubbed run answers every `zstub*` function before its first instruction, so the
difference between the two columns is the body and everything else stays
identical -- including the module-level code, whose qualname does not match.
"""

import os
import sys
import time

N = 200_000
REPS = 7


def zstub_pass(a, b):
    pass


def zstub_add(a, b):
    return a + b


def zstub_default(a, b=1, c=2):
    pass


def zstub_kw(a, b):
    pass


def zstub_many(a, b, c, d, e):
    pass


def loop_empty():
    for _ in range(N):
        pass


def loop_native_len():
    x = (1, 2)
    f = len
    for _ in range(N):
        f(x)


def loop_stub_pass():
    f = zstub_pass
    for _ in range(N):
        f(1, 2)


def loop_stub_add():
    f = zstub_add
    for _ in range(N):
        f(1, 2)


def loop_default_used():
    f = zstub_default
    for _ in range(N):
        f(1)


def loop_keyword_given():
    f = zstub_kw
    for _ in range(N):
        f(1, b=2)


def loop_five_positional():
    f = zstub_many
    for _ in range(N):
        f(1, 2, 3, 4, 5)


CASES = [
    ("empty_loop_floor", loop_empty),
    ("native_len", loop_native_len),
    ("stub_pass_body", loop_stub_pass),
    ("stub_add_body", loop_stub_add),
    ("default_used", loop_default_used),
    ("keyword_given", loop_keyword_given),
    ("five_positional", loop_five_positional),
]

mode = os.environ.get("LUNA_STUB_BODY", "") or "-"
print(f"== {sys.version.split()[0]} {sys.implementation.name} LUNA_STUB_BODY={mode}")
for label, fn in CASES:
    fn()  # one full pass warms the inline caches; the min-of-7 discards it
    best = None
    for _ in range(REPS):
        t0 = time.perf_counter()
        fn()
        dt = time.perf_counter() - t0
        ns = dt * 1e9 / N
        best = ns if best is None or ns < best else best
    print(f"{label:28s} {best:8.1f} ns/iter")
