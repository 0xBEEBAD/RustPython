"""Return-value shapes: does the frame exit clone something anyone will read?

`exitclone` restores the pre-fix traffic, where every frame exit built
`Some(value.clone())` before asking whether a trace or profile event was wanted.
Leaked values (None, small ints) only cost an acquire load, so the informative
cases hand back a real heap object, and the `deep*` cases multiply the number of
exits per loop iteration so the effect separates from the noise floor.

Usage: python exitclone_probe.py [N]
"""

import sys
import time

N = int(sys.argv[1]) if len(sys.argv) > 1 else 100_000
REPS = 3

TUPLE = (1, 2, 3)


class Thing:
    pass


INSTANCE = Thing()


def ret_none():
    pass


def ret_tuple():
    return TUPLE


def ret_instance():
    return INSTANCE


def l5():
    return TUPLE


def l4():
    return l5()


def l3():
    return l4()


def l2():
    return l3()


def l1():
    return l2()


def loop_floor():
    for _ in range(N):
        pass


def call_ret_none():
    for _ in range(N):
        ret_none()


def call_ret_tuple():
    for _ in range(N):
        ret_tuple()


def call_ret_instance():
    for _ in range(N):
        ret_instance()


def call_deep5_tuple():
    for _ in range(N):
        l1()


CASES = [
    ("empty_loop_floor", loop_floor),
    ("ret_none", call_ret_none),
    ("ret_tuple", call_ret_tuple),
    ("ret_instance", call_ret_instance),
    ("deep5_returns_tuple", call_deep5_tuple),
]

for name, fn in CASES:
    fn()
    best = None
    for _ in range(REPS):
        t0 = time.perf_counter()
        fn()
        dt = time.perf_counter() - t0
        best = dt if best is None else min(best, dt)
    print(f"{name:20s} {best / N * 1e9:8.1f} ns/iter")
