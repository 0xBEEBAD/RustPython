"""String-operation probe in ns/op (best of N), mirroring bench/strbench.py.

Applies the same differential loop baseline as the other probes so the method
dispatch cost is separated from the loop floor.
"""
import sys
import time

REPS = 5
N = 200_000
s = "abcdefghij" * 10


def b_loop(n):
    for _ in range(n):
        pass


def b_upper(n):
    for _ in range(n):
        s.upper()


def b_lower(n):
    for _ in range(n):
        s.lower()


def b_split(n):
    for _ in range(n):
        s.split("e")


def b_join(n):
    for _ in range(n):
        "-".join(["a", "b", "c"])


def b_format(n):
    for _ in range(n):
        "{}:{}".format(1, 2)


def b_find(n):
    for _ in range(n):
        s.find("fg")


def b_startswith(n):
    for _ in range(n):
        s.startswith("abc")


def b_slice(n):
    for _ in range(n):
        s[3:7]


def b_replace(n):
    for _ in range(n):
        s.replace("ab", "XY")


def b_len(n):
    for _ in range(n):
        len(s)


def b_concat(n):
    for _ in range(n):
        s + "!"


CASES = [
    ("loop only", b_loop),
    ("str.upper", b_upper),
    ("str.lower", b_lower),
    ("str.split", b_split),
    ("str.join", b_join),
    ("str.format", b_format),
    ("str.find", b_find),
    ("str.startswith", b_startswith),
    ("str slice", b_slice),
    ("str.replace", b_replace),
    ("len(str)", b_len),
    ("str concat", b_concat),
]


def main():
    print(f"=== {sys.implementation.name} ===")
    vals = {}
    for name, fn in CASES:
        best = float("inf")
        for _ in range(REPS):
            t0 = time.perf_counter()
            fn(N)
            dt = time.perf_counter() - t0
            if dt < best:
                best = dt
        vals[name] = best / N * 1e9
    base = vals["loop only"]
    for name, _ in CASES:
        print(f"{name:22s} {vals[name]:9.1f} ns   net {vals[name] - base:8.1f}")


if __name__ == "__main__":
    main()
