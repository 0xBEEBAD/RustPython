"""Which heap blocks does creating an exception cost?

`excprobe` splits raise/catch into create vs unwind; this splits *create* into
its allocations, which is what decides whether a freelist or an argument-passing
change is the lever. Run on the `alloc-stats` binary:

    target/allocstats/release/rustpython.exe bench/labs/allocexc.py
"""

import itertools
import sys

N = 100_000
repeat = itertools.repeat


def loop(n):
    for _ in repeat(None, n):
        pass


def ve_noargs(n):
    e = ValueError
    for _ in repeat(None, n):
        e()


def ve_onearg(n):
    e = ValueError
    for _ in repeat(None, n):
        e("x")


def ve_fourargs(n):
    e = ValueError
    for _ in repeat(None, n):
        e("a", "b", "c", "d")


def ve_new(n):
    e = ValueError
    nv = ValueError.__new__
    for _ in repeat(None, n):
        nv(e)


def ve_new_onearg(n):
    e = ValueError
    nv = ValueError.__new__
    for _ in repeat(None, n):
        nv(e, "x")


def raise_catch(n):
    for _ in repeat(None, n):
        try:
            raise ValueError("x")
        except ValueError:
            pass


def traceback_build(n):
    # Constructing an exception inside a `try` but never raising it isolates
    # the object from the unwind.
    e = ValueError
    for _ in repeat(None, n):
        try:
            x = e("x")
        except ValueError:
            pass


CASES = [
    ("loop floor", loop),
    ("ValueError()", ve_noargs),
    ("ValueError('x')", ve_onearg),
    ("ValueError(4 args)", ve_fourargs),
    ("__new__()", ve_new),
    ("__new__('x')", ve_new_onearg),
    ("try: exc = VE('x')", traceback_build),
    ("raise+catch", raise_catch),
]


def measure(fn):
    sys._alloc_stats(True)
    fn(N)
    return sys._alloc_stats(True)


def main():
    if not hasattr(sys, "_alloc_stats"):
        raise SystemExit("build with --features alloc-stats to use this probe")
    print(f"== {sys.version.split()[0]} {sys.implementation.name}")
    print(f"{'shape':<22} {'blocks/op':>10} {'bytes/op':>10}  sizes (all: count/op)")
    for name, fn in CASES:
        s = measure(fn)
        sizes = sorted(s["sizes"], key=lambda p: -p[1])
        top = " ".join(f"{size}:{count / N:.2f}" for size, count in sizes if count)
        print(f"{name:<22} {s['allocs'] / N:>10.3f} {s['bytes'] / N:>10.1f}  {top}")


if __name__ == "__main__":
    main()
