"""Decompose bench.py's worst case (`string ops`, 2.78x slower) one piece at a time.

bench_str is `s2 = s.upper() + "ij"` then `s2.split("d")` inside a range loop. The
rows below add exactly one piece to the loop floor, so the gap that matters -
attribute load, the call, the allocation the call returns, the concat - can be
attributed instead of assumed.

    python bench/labs/strcaseprobe.py
"""

import timeit

N = 200_000
s = "abcdefgh"
ij = "ij"
sep = "d"


def bench_str(n):
    s = "abcdefgh"
    for _ in range(n):
        s2 = s.upper() + "ij"
        s2.split("d")


SHAPES = [
    ("baseline: None", lambda: None),
    ("s.upper()", lambda: s.upper()),
    ("s.upper() + 'ij'", lambda: s.upper() + "ij"),
    ("s + 'ij' (no call)", lambda: s + "ij"),
    ("s.split('d')", lambda: s.split("d")),
    ("whole bench body", lambda: (s.upper() + "ij").split("d")),
    ("s.upper (load only)", lambda: s.upper),
    ("s.count('a')", lambda: s.count("a")),
    ("s.replace('a','b')", lambda: s.replace("a", "b")),
    ("s.strip()", lambda: s.strip()),
    ("s.lower()", lambda: s.lower()),
]

for name, fn in SHAPES:
    best = min(timeit.repeat(fn, number=N, repeat=3))
    print(f"{name:28s} {best / N * 1e9:7.1f} ns/iter")

# and the real case, timed the way bench.py times it
best = min(timeit.repeat(lambda: bench_str(1000), number=200, repeat=3))
print(f"{'bench_str(1000) per iter':28s} {best / 200 / 1000 * 1e9:7.1f} ns/iter")
