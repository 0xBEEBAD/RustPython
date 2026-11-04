"""Price the inside of `str.split`'s kernel, which the descriptor-arm ladder puts
at 288 ns of a 384 ns call - more than the arm (55) and the argument packing (30)
together.

Three gates cut it up, and all three only fire on a receiver whose text starts
with the `LUNA_STUB_STR` prefix, because they change the answer. Rows 4 and 5 use
a string without that prefix, so they are the filter's own control: they must not
move.

    LUNA_STUB_STR=zzp powershell -NoProfile -File bench/labs/ab.ps1 \
        -A target/release/rustpython.exe -B target/release/rustpython.exe \
        -Script bench/labs/splitinner.py -EnvA splbind -Rounds 5 -Mode ns
"""

import timeit

N = 300_000
p = "zzpabcdefgh"
q = "abcdefgh"

SHAPES = [
    ("baseline: None", lambda: None),
    ('p.split("q") 1 part', lambda: p.split("q")),
    ('p.split("d") 2 parts', lambda: p.split("d")),
    ('q.split("d") 2 parts CTRL', lambda: q.split("d")),
    ('q.casefold() CTRL', lambda: q.casefold()),
]

for name, fn in SHAPES:
    best = min(timeit.repeat(fn, number=N, repeat=3))
    print(f"{name:28s} {best / N * 1e9:7.1f} ns/iter")
