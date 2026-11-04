"""How many heap blocks, and which sizes, does an integer result cost?

The recorded numbers disagree with each other: one note says malachite already
stores one limb inline so a small `BigInt` needs no vector, the next says the
one block per range-loop iteration *is* malachite's digit buffer. This settles it
by windowing `sys._alloc_stats` over shapes that differ only in whether they
produce an int, and printing the size histogram so the block can be recognized.

Run on the alloc-stats build:

    target/allocstats/release/rustpython.exe bench/labs/intblocks.py [n]
"""

import itertools
import sys

N = int(sys.argv[1]) if len(sys.argv) > 1 else 100_000
repeat = itertools.repeat


def stats(reset=True):
    value = sys._alloc_stats(reset)
    if isinstance(value, dict):
        return value["allocs"], value["frees"], value["sizes"]
    return value


def window(label, fn):
    stats(True)
    fn(N)
    allocs, frees, sizes = stats(False)
    per = [f"{size}:{count / N:.3f}" for size, count in sorted(sizes) if count]
    print(f"{label:26s} blocks/op={(allocs - frees) / N + 0:.3f}  allocs/op={allocs / N:.3f}  {per}")


def floor(n):
    for _ in repeat(None, n):
        pass


def small_step(n):
    s = 0
    for i in range(n):
        s += i * 2 - 1
    return s


def range_iter(n):
    for i in range(n):
        pass


def one_add(n):
    a = 1
    for _ in repeat(None, n):
        b = a + 1
    return b


def big_add(n):
    a = 10**30
    for _ in repeat(None, n):
        b = a + 1
    return b


def new_int(n):
    for _ in repeat(None, n):
        b = int("12345")
    return b


def tuple_two(n):
    for _ in repeat(None, n):
        b = (1, 2)
    return b


print(f"== {sys.version} ==")
for name, fn in (
    ("floor (repeat loop)", floor),
    ("range iterator only", range_iter),
    ("one add of cached ints", one_add),
    ("bench arith s+=i*2-1", small_step),
    ("add to 10**30", big_add),
    ("int('12345')", new_int),
    ("(1, 2) tuple", tuple_two),
):
    window(name, fn)
