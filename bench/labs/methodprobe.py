"""Split a builtin method call into attribute load and call, on both interpreters.

`len(s)` costs 41 ns here but `s.isascii()` costs 126 ns, so the extra ~85 ns is
specific to the method path. These rows differ by exactly one piece: the same
name loaded without calling it, the same kernel reached as an unbound method with
an explicit self, and one-argument variants, so load cost and call cost can be
read apart instead of guessed.

    python bench/labs/methodprobe.py
"""

import timeit

N = 200_000
s = "abcdefgh"
isascii = s.isascii
upper = s.upper
str_isascii = str.isascii

SHAPES = [
    ("baseline: None", lambda: None),
    ("load s.isascii only", lambda: s.isascii),
    ("call s.isascii()", lambda: s.isascii()),
    ("call isascii (pre-bound)", lambda: isascii()),
    ("call str.isascii(s) unbound", lambda: str_isascii(s)),
    ("load s.upper only", lambda: s.upper),
    ("call s.upper()", lambda: s.upper()),
    ("call upper() pre-bound", lambda: upper()),
    ("call s.count('a') 1-arg method", lambda: s.count("a")),
    ("call str.count(s,'a') unbound", lambda: str.count(s, "a")),
    ("call len(s) builtin fn", lambda: len(s)),
    ("call hash(s) builtin fn", lambda: hash(s)),
    ("load s only (plain attr)", lambda: s.encode),
    ("call s.startswith('a')", lambda: s.startswith("a")),
]

for name, fn in SHAPES:
    best = min(timeit.repeat(fn, number=N, repeat=3))
    print(f"{name:34s} {best / N * 1e9:7.1f} ns/iter")
