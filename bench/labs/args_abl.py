"""Blocks/iteration for the paths that still run `__new__` + `__init__`.

The `excctor` fast path (frame.rs, ablatable with `LUNA_ABLATE=excctor`) already
constructs well-known builtin exception types directly, so `ValueError(i)` in
bench_exc builds one args tuple and never reaches `BaseException.__init__`.
Put the ablation back and the generic `type.__call__` route is measured again,
along with the shapes that were never on the fast path: a Python subclass of an
exception, `type(e)(*args)`, and retained instances (which starve the tuple
freelist, so each PyTuple shows up as its own block).

Run (alloc-stats build):
    LUNA_ABLATE=      <exe> bench/labs/args_abl.py
    LUNA_ABLATE=excctor <exe> bench/labs/args_abl.py
"""

import itertools
import sys

N = 500_000
RETAIN_N = 200_000
repeat = itertools.repeat


class SubValue(ValueError):
    pass


class SubOSError(OSError):
    pass


def throw(i):
    raise ValueError(i)


def bench_exc(n):
    caught = 0
    for i in range(n):
        try:
            throw(i)
        except ValueError:
            caught += 1


def create_sub(n):
    for _ in repeat(None, n):
        SubValue("x")


def create_oserror(n):
    for _ in repeat(None, n):
        OSError(2, "msg")


def reflect_type_call(n):
    e = ValueError("x")
    cls = type(e)
    for _ in repeat(None, n):
        cls("x")


def retain_sub(n):
    keep = [None] * n
    for i in range(n):
        keep[i] = SubValue("x")


def retain_oserror(n):
    keep = [None] * n
    for i in range(n):
        keep[i] = OSError(2, "msg")


CASES = [
    ("bench_exc", bench_exc, N),
    ("create subclass", create_sub, N),
    ("create OSError", create_oserror, N),
    ("type(e)(x) call", reflect_type_call, N),
    ("retain subclass", retain_sub, RETAIN_N),
    ("retain OSError", retain_oserror, RETAIN_N),
]


def measure(fn, n):
    sys._alloc_stats(True)
    fn(n)
    return sys._alloc_stats(True)


def main():
    import os

    print(f"LUNA_ABLATE={os.environ.get('LUNA_ABLATE', '')}")
    print(f"{'shape':<20} {'allocs/op':>10} {'frees/op':>10} {'bytes/op':>10}")
    for name, fn, n in CASES:
        s = measure(fn, n)
        print(f"{name:<20} {s['allocs']/n:>10.3f} {s['frees']/n:>10.3f} {s['bytes']/n:>10.1f}")


if __name__ == "__main__":
    if not hasattr(sys, "_alloc_stats"):
        raise SystemExit("build with --features alloc-stats to use this probe")
    main()
