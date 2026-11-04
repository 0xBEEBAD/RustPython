"""Which part of a keyword/default call costs 187 ns over CPython?

callprobe.py shows `call_kw_default` at 233.5 ns vs CPython 46.4 while a plain
two-positional call is 145.2. This probe splits that into the shapes the binder
takes different paths through: exact positionals (no defaults consulted),
defaults actually filled, a keyword given for a defaulted parameter, keyword-only
defaults and **kwargs absorption.

Each case owns its loop and calls the target directly - routing through a lambda
would add the very call we are measuring.
"""

import sys
import time

N = 200_000
REPS = 7


def two(a, b):
    pass


def dflt(a, b=1):
    pass


def kwonly(a, *, b=1):
    pass


def many_dflt(a, b=1, c=2, d=3):
    pass


def varkw(a, **kw):
    pass


def loop_empty():
    for _ in range(N):
        pass


def loop_two_positional():
    f = two
    for _ in range(N):
        f(1, 2)


def loop_exact_with_default_given():
    f = dflt
    for _ in range(N):
        f(1, 2)


def loop_default_used():
    f = dflt
    for _ in range(N):
        f(1)


def loop_keyword_for_defaulted():
    f = dflt
    for _ in range(N):
        f(1, b=2)


def loop_kwonly_default_used():
    f = kwonly
    for _ in range(N):
        f(1)


def loop_kwonly_given():
    f = kwonly
    for _ in range(N):
        f(1, b=2)


def loop_three_defaults_used():
    f = many_dflt
    for _ in range(N):
        f(1)


def loop_three_all_given():
    f = many_dflt
    for _ in range(N):
        f(1, 2, 3, 4)


def loop_varkw_empty():
    f = varkw
    for _ in range(N):
        f(1)


def loop_varkw_one():
    f = varkw
    for _ in range(N):
        f(1, x=2)


CASES = [
    ("empty_loop_floor", loop_empty),
    ("two_positional", loop_two_positional),
    ("exact_with_default_given", loop_exact_with_default_given),
    ("default_used", loop_default_used),
    ("keyword_for_defaulted", loop_keyword_for_defaulted),
    ("kwonly_default_used", loop_kwonly_default_used),
    ("kwonly_given", loop_kwonly_given),
    ("three_defaults_used", loop_three_defaults_used),
    ("three_all_given", loop_three_all_given),
    ("varkw_empty", loop_varkw_empty),
    ("varkw_one", loop_varkw_one),
]

print("==", sys.version.split()[0], sys.implementation.name)
floor = None
for label, fn in CASES:
    fn()  # one full pass warms the inline caches; the min-of-7 discards it
    best = None
    for _ in range(REPS):
        t0 = time.perf_counter()
        fn()
        dt = time.perf_counter() - t0
        ns = dt * 1e9 / N
        best = ns if best is None or ns < best else best
    if floor is None:
        floor = best
    print(f"{label:28s} {best:8.1f} ns/iter   net {best - floor:8.1f}")
