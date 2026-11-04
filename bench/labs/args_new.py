"""Blocks/iteration for the one path that still runs both `__new__` and
`__init__` on an exception: a class with a Python-level `__new__`.

`type.__call__` cannot skip the init call for such a class (its new slot is the
Python `new_wrapper`), so `BaseException.__init__` receives the cloned args and
used to re-pack them into a second tuple. Retained instances starve the tuple
freelist, so the husk shows up as its own block.

Run (alloc-stats build):
    <exe> bench/labs/args_new.py
"""

import itertools
import sys

N = 200_000
repeat = itertools.repeat


class NewOnly(ValueError):
    def __new__(cls, *a, **kw):
        return Exception.__new__(cls, *a)


class NewAndInit(ValueError):
    def __new__(cls, *a, **kw):
        return Exception.__new__(cls, *a)

    def __init__(self, *a, **kw):
        super().__init__(*a)


def create_new(n):
    for _ in repeat(None, n):
        NewOnly("x")


def retain_new(n):
    keep = [None] * n
    for i in range(n):
        keep[i] = NewOnly("x")


def retain_new_init(n):
    keep = [None] * n
    for i in range(n):
        keep[i] = NewAndInit("x")


def pickle_roundtrip(n):
    import pickle

    dumps = pickle.dumps
    loads = pickle.loads
    for _ in repeat(None, n):
        loads(dumps(NewOnly("x")))


CASES = [
    ("create NewOnly", create_new, N),
    ("retain NewOnly", retain_new, N),
    ("retain New+Init", retain_new_init, N),
    ("pickle NewOnly", pickle_roundtrip, N),
]


def measure(fn, n):
    sys._alloc_stats(True)
    fn(n)
    return sys._alloc_stats(True)


def main():
    print(f"{'shape':<18} {'allocs/op':>10} {'frees/op':>10} {'bytes/op':>10}")
    for name, fn, n in CASES:
        s = measure(fn, n)
        print(f"{name:<18} {s['allocs']/n:>10.3f} {s['frees']/n:>10.3f} {s['bytes']/n:>10.1f}")


if __name__ == "__main__":
    if not hasattr(sys, "_alloc_stats"):
        raise SystemExit("build with --features alloc-stats to use this probe")
    main()
