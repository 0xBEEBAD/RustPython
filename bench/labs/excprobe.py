"""Price exception construction and raising, the shape #69's slot change could cost.

`ValueError('boom')` and `MyError('boom')` now reach `BaseException.__init__`
through `type.__call__`, where before they skipped it - and `type.__call__` has to
hand the initializer its own `FuncArgs`, because `__new__` consumed the first one.
That clone is the cost this probe measures, separately for the three paths a
builtin exception can take: the direct constructor fast path in the CALL arm, the
plain `type.__call__` route, and a user subclass, which always went through
`type.__call__` and so should not have moved at all.

    python bench/labs/excprobe.py [reps]
"""

import time

ITER = 100_000
REPS = int(__import__("sys").argv[1]) if len(__import__("sys").argv) > 1 else 7


class MyError(Exception):
    pass


class OSErrorLike(OSError):
    pass


def builtin_raise(n):
    for _ in range(n):
        try:
            raise ValueError("boom")
        except ValueError:
            pass


def user_raise(n):
    for _ in range(n):
        try:
            raise MyError("boom")
        except MyError:
            pass


def oserror_raise(n):
    for _ in range(n):
        try:
            raise OSErrorLike(2, "no such file")
        except OSErrorLike:
            pass


def builtin_construct(n):
    sink = None
    for _ in range(n):
        sink = ValueError("boom")
    return sink


def user_construct(n):
    sink = None
    for _ in range(n):
        sink = MyError("boom")
    return sink


def oserror_construct(n):
    sink = None
    for _ in range(n):
        sink = OSErrorLike(2, "no such file")
    return sink


def positional_only(n):
    # The `plain_exceptions` fast path in the CALL arm: no keyword names at all.
    sink = None
    for _ in range(n):
        sink = TypeError("bad")
    return sink


def slot_wrapper(n):
    # `ValueError.__call__` is type.__call__ itself, so this reaches the
    # interpreter's class-call route with nothing specialized and no CALL-arm
    # direct constructor - the route the `excinit` fast path changes.
    make = ValueError.__call__
    sink = None
    for _ in range(n):
        sink = make("bad")
    return sink


def explicit_type_call(n):
    tp_call = type.__call__
    sink = None
    for _ in range(n):
        sink = tp_call(ValueError, "bad")
    return sink


def heap_subclass_call(n):
    # A Python subclass keeps its own inherited initializer, so it must still run
    # it: same args, and no fast path.
    sink = None
    for _ in range(n):
        sink = SubError("bad")
    return sink


def timeit(fn):
    best = None
    for _ in range(REPS):
        started = time.perf_counter()
        fn(ITER)
        elapsed = time.perf_counter() - started
        if best is None or elapsed < best:
            best = elapsed
    return 1e9 * best / ITER


class SubError(Exception):
    pass


class Point:
    def __init__(self, x):
        self.x = x


def plain_class_call(n):
    # The path the new slot comparison has to leave alone: an ordinary class with
    # its own `__init__`, whose arguments therefore must be cloned and passed on.
    sink = None
    for _ in range(n):
        sink = Point(1)
    return sink


for name, fn in (
    ("builtin_raise", builtin_raise),
    ("user_raise", user_raise),
    ("oserror_raise", oserror_raise),
    ("builtin_construct", builtin_construct),
    ("user_construct", user_construct),
    ("oserror_construct", oserror_construct),
    ("positional_only", positional_only),
    ("slot_wrapper", slot_wrapper),
    ("explicit_type_call", explicit_type_call),
    ("heap_subclass_call", heap_subclass_call),
    ("plain_class_call", plain_class_call),
):
    print(f"{name:20s} {timeit(fn):7.2f} ns/iter")
