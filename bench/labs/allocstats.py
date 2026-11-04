"""Allocation volume per interpreter shape, using the `alloc-stats` build.

`cargo build --features alloc-stats` wraps the global allocator in counters and
publishes `sys._alloc_stats(reset)`. This probe runs one shape per measurement
window and reports blocks and bytes per iteration, with every shape built on
the same `repeat` loop so the loop itself is the baseline that cancels.

Run:
    ../temp/rp-allocstats.exe bench/labs/allocstats.py
and read `blocks/op` - that is what decides whether an allocation-shaped
refactor (inline tuple elements, single-block exception args, embedded frame in
generator) is worth its risk, which ns/op alone cannot tell.
"""
import itertools
import sys

N = 200_000
repeat = itertools.repeat


def noop(x):
    return x


class Point:
    def m(self, x):
        return x


obj = Point()


def loop(n):
    for _ in repeat(None, n):
        pass


def call(n):
    for _ in repeat(None, n):
        noop(1)


def method(n):
    for _ in repeat(None, n):
        obj.m(1)


def tuple2(n):
    a = 1
    b = 2
    for _ in repeat(None, n):
        x = (a, b)


def tuple2_mutable(n):
    # A tuple whose elements are produced at run time, which is what a call
    # site with `*args` or a returned pair actually looks like.
    obj = [1]
    for _ in repeat(None, n):
        x = (obj[0], obj[0])


def args_tuple(n):
    def f(*args):
        return args

    for _ in repeat(None, n):
        f(1, 2)


def kwargs_call(n):
    def g(a=None, b=None):
        return a

    for _ in repeat(None, n):
        g(b=2)


def tuple0(n):
    for _ in repeat(None, n):
        x = tuple([])


def tuple1(n):
    a = 1
    for _ in repeat(None, n):
        x = (a,)


def tuple4(n):
    a = 1
    b = 2
    for _ in repeat(None, n):
        x = (a, b, a, b)


def empty_container_floor(n):
    # Tells what an *empty* container costs, so the tuple arity curve can be
    # read as "fixed blocks + scaling block".
    for _ in repeat(None, n):
        x = []


def bound_method_value(n):
    for _ in repeat(None, n):
        m = obj.m


def list2(n):
    for _ in repeat(None, n):
        x = [1, 2]


def dict1(n):
    for _ in repeat(None, n):
        x = {"k": 1}


def set1(n):
    for _ in repeat(None, n):
        x = {1}


def concat(n):
    a, b = "aaaa", "bbbb"
    for _ in repeat(None, n):
        x = a + b


def fmt(n):
    a = "aaaa"
    for _ in repeat(None, n):
        x = "%s" % a


def slice_(n):
    t = (1, 2, 3, 4)
    for _ in repeat(None, n):
        x = t[1:3]


def raise_catch(n):
    for _ in repeat(None, n):
        try:
            raise ValueError("x")
        except ValueError as e:
            pass


def gen_next(n):
    g = (i for i in range(n))
    for _ in g:
        pass


def genexpr_list(n):
    x = [i for i in range(n)]


def range_iter(n):
    for i in range(n):
        pass


CASES = [
    ("loop", loop),
    ("call", call),
    ("method", method),
    ("tuple(1,2)", tuple2),
    ("tuple runtime", tuple2_mutable),
    ("tuple()", tuple0),
    ("tuple(a,)", tuple1),
    ("tuple(a,b,a,b)", tuple4),
    ("list []", empty_container_floor),
    ("*args call", args_tuple),
    ("kwargs call", kwargs_call),
    ("obj.m value", bound_method_value),
    ("list[1,2]", list2),
    ("dict{k:1}", dict1),
    ("set{1}", set1),
    ("str concat", concat),
    ("str %s", fmt),
    ("tuple slice", slice_),
    ("raise+catch", raise_catch),
    ("genexpr next", gen_next),
    ("list comp", genexpr_list),
    ("for range", range_iter),
]


def measure(fn):
    sys._alloc_stats(True)  # arm a clean window
    fn(N)
    stats = sys._alloc_stats(True)
    return stats


def main():
    print(f"{'shape':<14} {'blocks/op':>10} {'bytes/op':>10}  sizes (rounded: count/op)")
    results = {}
    for name, fn in CASES:
        s = measure(fn)
        blocks = s["allocs"] / N
        bytes_ = s["bytes"] / N
        sizes = sorted(s["sizes"], key=lambda p: -p[1])
        top = " ".join(f"{size}:{count / N:.2f}" for size, count in sizes[:4])
        results[name] = blocks
        print(f"{name:<14} {blocks:>10.3f} {bytes_:>10.1f}  {top}")
    print()
    print("loop floor blocks/op:", round(results["loop"], 3))


if __name__ == "__main__":
    if not hasattr(sys, "_alloc_stats"):
        raise SystemExit("build with --features alloc-stats to use this probe")
    main()
