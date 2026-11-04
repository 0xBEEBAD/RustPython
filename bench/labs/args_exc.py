"""Args-tuple probe: blocks/iteration on the exception-creation path.

Uses the `alloc-stats` build (`sys._alloc_stats(reset)`) to count allocated
blocks per iteration for shapes that differ only in how an exception is built,
so a redundant args tuple shows up as a whole block.

`bench_exc` is the shape from bench/bench.py (a `throw(i)` helper that raises
`ValueError(i)`), reproduced here so the number is comparable to the bench.
`raise prebuilt` is run at a smaller N: re-raising one exception object a
million times builds a context chain that overflows the stack when the
interpreter drops it (pre-existing, unrelated to args plumbing).

Run:
    <alloc-stats exe> bench/labs/args_exc.py
"""

import itertools
import sys

N = 1_000_000
SMALL_N = 100_000
RETAIN_N = 200_000
repeat = itertools.repeat


def throw(i):
    raise ValueError(i)


def loop(n):
    for _ in repeat(None, n):
        pass


def bench_exc(n):
    caught = 0
    for i in range(n):
        try:
            throw(i)
        except ValueError:
            caught += 1


def raise_catch(n):
    # the bench_exc shape without the helper call
    for _ in repeat(None, n):
        try:
            raise ValueError("x")
        except ValueError:
            pass


def create_only(n):
    for _ in repeat(None, n):
        ValueError("x")


def create_no_arg(n):
    for _ in repeat(None, n):
        ValueError()


def create_two_args(n):
    for _ in repeat(None, n):
        ValueError("x", "y")


def create_subclass(n):
    exc = type("E", (ValueError,), {})
    for _ in repeat(None, n):
        exc("x")


def create_override_new(n):
    # __new__ override, native __init__ still inherited
    exc = type("N", (ValueError,), {"__new__": lambda cls, *a: ValueError.__new__(cls, *a)})
    for _ in repeat(None, n):
        exc("x")


def raise_prebuilt(n):
    e = ValueError("x")
    for _ in repeat(None, n):
        try:
            raise e
        except ValueError:
            pass


def tuple_create(n):
    # reference cost of one 1-element tuple materialization
    a = "x"
    for _ in repeat(None, n):
        t = (a,)


def retain_exc(n):
    # Exceptions kept alive: nothing is freed, so the tuple freelist cannot
    # recycle and every PyTuple::new_ref shows up as a real block.
    keep = [None] * n
    for i in range(n):
        keep[i] = ValueError("x")


def retain_tuple(n):
    keep = [None] * n
    for i in range(n):
        keep[i] = ("x",)


CASES = [
    ("loop floor", loop, N),
    ("bench_exc throw()", bench_exc, N),
    ("raise+catch", raise_catch, N),
    ("create ValueError(x)", create_only, N),
    ("create ValueError()", create_no_arg, N),
    ("create V(x,y)", create_two_args, N),
    ("create subclass", create_subclass, N),
    ("create override new", create_override_new, N),
    ("tuple (a,)", tuple_create, N),
    ("retain exc", retain_exc, RETAIN_N),
    ("retain tuple", retain_tuple, RETAIN_N),
    ("raise prebuilt", raise_prebuilt, SMALL_N),
]


def measure(fn, n=N):
    sys._alloc_stats(True)
    fn(n)
    return sys._alloc_stats(True)


def main():
    print(f"{'shape':<22} {'blocks/op':>10} {'bytes/op':>10}  sizes (bucket: count/op)")
    out = {}
    for name, fn, n in CASES:
        s = measure(fn, n)
        blocks = s["allocs"] / n
        bytes_ = s["bytes"] / n
        sizes = sorted(s["sizes"], key=lambda p: -p[1])
        top = " ".join(f"{size}:{count / n:.3f}" for size, count in sizes[:5] if count)
        out[name] = blocks
        print(f"{name:<22} {blocks:>10.3f} {bytes_:>10.1f}  {top}")
    print()
    print("net blocks/op over loop floor:")
    for name, _, _ in CASES:
        print(f"  {name:<22} {out[name] - out['loop floor']:.3f}")


if __name__ == "__main__":
    if not hasattr(sys, "_alloc_stats"):
        raise SystemExit("build with --features alloc-stats to use this probe")
    main()
