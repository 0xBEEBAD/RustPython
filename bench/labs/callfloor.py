"""Call-floor decomposition with a prefix that cannot collide with the stdlib.

`LUNA_STUB_BODY` stubs any function whose qualname starts with the prefix, so a
one-letter prefix stubs the interpreter's own startup helpers and the process
never boots. Every callee here starts with `zzcallfloor`, which nothing in the
standard library does.

Run the same file under four configurations on one binary:

    (none)                                   dispatch + frame + body
    LUNA_STUB_BODY=zzcallfloor               dispatch + frame (body stubbed)
    LUNA_ABLATE=noenter LUNA_STUB_BODY=...   dispatch + frame build only

and subtract neighbours: body = row0 - row1, run_frame entry/exit = row1 - row2.
"""

import sys
import time

N = 200_000
REPS = 5


def zzcallfloor0():
    pass


def zzcallfloor2(a, b):
    pass


def zzcallfloor_add(a, b):
    return a + b


class ZzHolder:
    def zzcallfloor_m(self, a):
        pass


def zzcallfloor_wide8(a, b, c, d, e, f, g, h):
    pass


def zzcallfloor_local8():
    a1 = a2 = a3 = a4 = a5 = a6 = a7 = a8 = 1


zz_outer = 1


def zzcallfloor_make():
    v = 1

    def zzcallfloor_inner():
        return v

    return zzcallfloor_inner


zz_clf = zzcallfloor_make()


zz_obj = ZzHolder()


def loop_empty():
    for _ in range(N):
        pass


def loop_0():
    f = zzcallfloor0
    for _ in range(N):
        f()


def loop_2():
    f = zzcallfloor2
    for _ in range(N):
        f(1, 2)


def loop_add():
    f = zzcallfloor_add
    for _ in range(N):
        f(1, 2)


def loop_method_cached():
    m = zz_obj.zzcallfloor_m
    for _ in range(N):
        m(1)


def loop_method_attr():
    o = zz_obj
    for _ in range(N):
        o.zzcallfloor_m(1)


def loop_wide8():
    f = zzcallfloor_wide8
    for _ in range(N):
        f(1, 2, 3, 4, 5, 6, 7, 8)


def loop_local8():
    f = zzcallfloor_local8
    for _ in range(N):
        f()


def loop_closure():
    f = zz_clf
    for _ in range(N):
        f()


CASES = [
    ("empty", loop_empty),
    ("call_0", loop_0),
    ("call_2", loop_2),
    ("call_add", loop_add),
    ("wide8", loop_wide8),
    ("local8", loop_local8),
    ("closure", loop_closure),
    ("method_cached", loop_method_cached),
    ("method_attr", loop_method_attr),
]

print("==", sys.version.split()[0], sys.implementation.name)
for label, fn in CASES:
    fn()
    best = None
    for _ in range(REPS):
        t0 = time.perf_counter()
        fn()
        dt = time.perf_counter() - t0
        ns = dt * 1e9 / N
        best = ns if best is None or ns < best else best
    print(f"{label:12s} {best:8.1f} ns/iter")
