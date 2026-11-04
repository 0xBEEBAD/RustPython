"""Split the `s.split(sep)` cost, which is the biggest single item in bench.py's
worst case (`string ops`, 2.78x CPython).

bench_str ends every iteration with `s2.split("d")`, worth 379 ns here against
CPython's 83. These rows keep the call and change only what it produces - one
part, two parts, three parts, a tuple instead of a list, a partition - so the
answer says whether the money is in the descriptor arm, the separator scan, or the
objects the kernel allocates.

    python bench/labs/splitprobe.py
"""

import timeit

N = 200_000
s = "abcdefgh"
u = "abcddefghd"
v = "abcd-def-gh"

SHAPES = [
    ("baseline: None", lambda: None),
    ('s.split("d") 2 parts', lambda: s.split("d")),
    ('s.split("zz") 1 part', lambda: s.split("zz")),
    ('u.split("d") 4 parts', lambda: u.split("d")),
    ('v.split("-") 3 parts', lambda: v.split("-")),
    ('v.split("-", 1) 2 parts', lambda: v.split("-", 1)),
    ('v.split() 3 parts', lambda: v.split()),
    ('v.partition("-")', lambda: v.partition("-")),
    ('v.rpartition("-")', lambda: v.rpartition("-")),
    ('u.replace("d", "e")', lambda: u.replace("d", "e")),
    ('u.removeprefix("ab")', lambda: u.removeprefix("ab")),
    ('v.strip("-")', lambda: v.strip("-")),
    ("list(v)", lambda: list(v)),
    ("tuple(v)", lambda: tuple(v)),
    ('v.casefold()', lambda: v.casefold()),
]

for name, fn in SHAPES:
    best = min(timeit.repeat(fn, number=N, repeat=3))
    print(f"{name:28s} {best / N * 1e9:7.1f} ns/iter")
