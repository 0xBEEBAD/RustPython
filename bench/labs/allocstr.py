"""Allocation volume for the string shapes that make `string ops` bench.py's
worst case (2.78x CPython), on the `alloc-stats` build.

The descriptor-arm ladder says the split *callee* costs 288 ns while the arm
costs 55 and the argument packing 30, so the money is inside the kernel. This
probe decides whether that is allocator traffic or code: every shape runs
inside the same `repeat` loop, so `loop` is the baseline that cancels.

Run:
    target/release/rustpython.exe bench/labs/allocstr.py
"""
import itertools
import sys

N = 200_000
repeat = itertools.repeat

s = "abcdefgh"
v = "abcd-def-gh"


def loop(n):
    for _ in repeat(None, n):
        pass


def split_1_part(n):
    for _ in repeat(None, n):
        s.split("zz")


def split_2_parts(n):
    for _ in repeat(None, n):
        s.split("d")


def split_4_parts(n):
    for _ in repeat(None, n):
        v.split("-")


def casefold(n):
    for _ in repeat(None, n):
        v.casefold()


def strip(n):
    for _ in repeat(None, n):
        v.strip("-")


def upper(n):
    for _ in repeat(None, n):
        s.upper()


def bench_str(n):
    # Exactly bench.py's bench_str body.
    for _ in repeat(None, n):
        s2 = s.upper() + "ij"
        s2.split("d")


def join3(n):
    parts = ["a", "b", "c"]
    for _ in repeat(None, n):
        "".join(parts)


def list_of_chars(n):
    for _ in repeat(None, n):
        list(v)


CASES = [
    ("loop", loop),
    ("split 1 part", split_1_part),
    ("split 2 parts", split_2_parts),
    ("split 3 parts", split_4_parts),
    ("casefold", casefold),
    ("strip", strip),
    ("upper", upper),
    ("bench_str", bench_str),
    ("join 3", join3),
    ("list(str)", list_of_chars),
]


def main():
    print(f"{'shape':<14} {'blocks/op':>10} {'bytes/op':>10}  sizes (rounded: count/op)")
    floor = None
    for name, fn in CASES:
        sys._alloc_stats(True)
        fn(N)
        stats = sys._alloc_stats(True)
        blocks = stats["allocs"] / N
        if floor is None:
            floor = blocks
        sizes = sorted(stats["sizes"], key=lambda p: -p[1])
        top = " ".join(f"{size}:{count / N:.2f}" for size, count in sizes[:5])
        print(f"{name:<14} {blocks:>10.3f} {stats['bytes'] / N:>10.1f}  {top}"
              f"   net {blocks - floor:+.3f}")
    print()
    print("blocks/op above is gross; net column subtracts the loop floor.")


if __name__ == "__main__":
    if not hasattr(sys, "_alloc_stats"):
        raise SystemExit("build with --features alloc-stats to use this probe")
    main()
