"""Call-cost decomposition, ns per iteration, all on the same loop floor.

The loop floor itself is ~22 ns here and ~12 ns on CPython 3.14, so every case
below is ~its number minus the `empty` case. Written because `LUNA_ABLATE=stubcall`
cannot boot the interpreter (it stubs the calls `sys` is built with), so the
callee-vs-dispatch split has to be measured by shaping the body instead.
"""
import time

N = 200_000
REPS = 5


def g0():
    pass


def g1(a):
    pass


def g2(a, b):
    pass


def g3(a, b, c):
    pass


def add2(a, b):
    return a + b


def gvar(*args):
    pass


def gkw(a, b=1):
    pass


class C:
    def m(self, a):
        pass


class S:
    __slots__ = ("x",)

    def __init__(self, x):
        self.x = x


obj = C()
one = [1]
KEY = "k"
D = {KEY: 1}


def empty():
    for _ in range(N):
        pass


def call0():
    for _ in range(N):
        g0()


def call1():
    for _ in range(N):
        g1(1)


def call2():
    for _ in range(N):
        g2(1, 2)


def call3():
    for _ in range(N):
        g3(1, 2, 3)


def call_add():
    for _ in range(N):
        add2(1, 2)


def inline_add():
    for _ in range(N):
        1 + 2


def call_method():
    for _ in range(N):
        obj.m(1)


def call_varargs():
    for _ in range(N):
        gvar(1, 2, 3)


def call_default_kw():
    for _ in range(N):
        gkw(1, b=2)


def call_builtin_len():
    for _ in range(N):
        len(one)


def call_builtin_dict():
    for _ in range(N):
        D.get(KEY)


def new_slotted():
    for _ in range(N):
        S(1)


def new_plain():
    for _ in range(N):
        C()


CASES = [
    ("empty", empty),
    ("call_0arg", call0),
    ("call_1arg", call1),
    ("call_2arg", call2),
    ("call_3arg", call3),
    ("call_add_body", call_add),
    ("inline_add_no_call", inline_add),
    ("method_1arg", call_method),
    ("call_varargs", call_varargs),
    ("call_kw_default", call_default_kw),
    ("builtin_len", call_builtin_len),
    ("builtin_dict_get", call_builtin_dict),
    ("new_slotted", new_slotted),
    ("new_plain_class", new_plain),
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
