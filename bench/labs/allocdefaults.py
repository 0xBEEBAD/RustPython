"""Blocks allocated per call shape, to settle where a defaulted call's cost is.

Run the same probe twice on the `alloc-stats` binary, with and without
`LUNA_ABLATE=defbind`:

    target/allocstats/release/rustpython.exe bench/labs/allocdefaults.py
    LUNA_ABLATE=defbind target/allocstats/release/rustpython.exe bench/labs/allocdefaults.py

If a row's `blocks/op` is the same in both runs, the fast path is not taken (or
does not change the allocation shape), and no amount of tuning its timing means
anything. Rows are the same call sites allocdefaults measures against CPython.

The exception and generator rows ride along because they are the next levers
ranked by cost: `ValueError(1)`, a raise/catch pair, a generator's create and
its first `next`.
"""

import itertools
import os
import sys

N = 100_000
repeat = itertools.repeat


def two(a, b):
    pass


def dflt(a, b=1):
    pass


def many(a, b=1, c=2, d=3):
    pass


def all_dflt(a=1, b=2):
    pass


def gen(a, b=1):
    yield a


def one_arg(a):
    pass


class Method:
    def exact(self, x):
        pass

    def dflt(self, x=1):
        pass


method_obj = Method()


class Plain:
    pass


plain_obj = Plain()
str_val = "abcdefgh"
dict_val = {"k": 1}
list_val = [1, 2, 3]


def loop(n):
    for _ in repeat(None, n):
        pass


def exact_call(n):
    f = two
    for _ in repeat(None, n):
        f(1, 2)


def default_one(n):
    f = dflt
    for _ in repeat(None, n):
        f(1)


def default_three(n):
    f = many
    for _ in repeat(None, n):
        f(1)


def default_zero(n):
    f = all_dflt
    for _ in repeat(None, n):
        f()


def exc_valueerror(n):
    e = ValueError
    for _ in repeat(None, n):
        e(1)


def exc_raise_catch(n):
    for _ in repeat(None, n):
        try:
            raise ValueError(1)
        except ValueError:
            pass


def gen_create(n):
    g = gen
    for _ in repeat(None, n):
        g(1)


def exact_one_arg(n):
    f = one_arg
    for _ in repeat(None, n):
        f(1)


def default_two_of_four(n):
    f = many
    for _ in repeat(None, n):
        f(1, 2)


def method_exact(n):
    m = method_obj.exact
    for _ in repeat(None, n):
        m(1)


def method_default(n):
    m = method_obj.dflt
    for _ in repeat(None, n):
        m()


def method_attr_default(n):
    for _ in repeat(None, n):
        method_obj.dflt()


def builtin_len(n):
    for _ in repeat(None, n):
        len(str_val)


def str_upper(n):
    for _ in repeat(None, n):
        str_val.upper()


def str_split(n):
    for _ in repeat(None, n):
        str_val.split("d")


def dict_get(n):
    for _ in repeat(None, n):
        dict_val.get("k")


def class_new(n):
    c = Plain
    for _ in repeat(None, n):
        c()


def list_index(n):
    for _ in repeat(None, n):
        list_val[1]


CASES = [
    ("loop floor", loop),
    ("exact 1 arg", exact_one_arg),
    ("exact 2 args", exact_call),
    ("default 1 of 2", default_one),
    ("default 0 of 2", default_zero),
    ("default 1 of 4", default_three),
    ("default 2 of 4", default_two_of_four),
    ("method exact", method_exact),
    ("method default", method_default),
    ("method+attr default", method_attr_default),
    ("builtin len", builtin_len),
    ("str.upper", str_upper),
    ("str.split", str_split),
    ("dict.get", dict_get),
    ("class C()", class_new),
    ("list index", list_index),
    ("ValueError(1)", exc_valueerror),
    ("raise+catch VE", exc_raise_catch),
    ("gen(1) create", gen_create),
]


def measure(fn):
    sys._alloc_stats(True)
    fn(N)
    return sys._alloc_stats(True)


def main():
    if not hasattr(sys, "_alloc_stats"):
        raise SystemExit("build with --features alloc-stats to use this probe")
    abl = os.environ.get("LUNA_ABLATE", "")
    print(f"== {sys.version.split()[0]} {sys.implementation.name}  LUNA_ABLATE={abl or '(none)'}")
    print(f"{'shape':<16} {'blocks/op':>10} {'bytes/op':>10}  sizes (rounded: count/op)")
    for name, fn in CASES:
        s = measure(fn)
        sizes = sorted(s["sizes"], key=lambda p: -p[1])
        top = " ".join(f"{size}:{count / N:.2f}" for size, count in sizes if count)
        print(f"{name:<16} {s['allocs'] / N:>10.3f} {s['bytes'] / N:>10.1f}  {top}")


if __name__ == "__main__":
    main()
