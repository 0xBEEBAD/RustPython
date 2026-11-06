"""Bytes-object churn, to decide things bench.py cannot see.

bench.py has twelve cases and none of them allocates a bytes object, so a
change to the bytes object model is unmeasurable there - "neutral on bench" is
the expected result whether or not the change helps. This probe produces the
same `name  ops/s` lines bench.py does, so bench/labs/ab.ps1 can price two
binaries with it:

    powershell -NoProfile -File bench/labs/ab.ps1 -A <old.exe> -B <new.exe> \
        -Script bench/labs/bitchurn.py -Mode ops -Rounds 3

Each shape is timed on its own so a win that only exists for, say, slicing is
not averaged away by shapes that never touch the allocator.
"""

import itertools
import sys
import time

ROUNDS = 5
N = 400_000
repeat = itertools.repeat

TEXT = "abcdefghij"
BLOB = b"the quick brown fox jumps over the lazy dog"
CHUNK = BLOB[:8]


def shape_encode():
    for _ in repeat(None, N):
        TEXT.encode()


def shape_slice():
    for _ in repeat(None, N):
        BLOB[:8]


def shape_ctor():
    for _ in repeat(None, N):
        bytes(CHUNK)


def shape_join():
    for _ in repeat(None, N):
        b"".join((CHUNK, CHUNK))


def shape_str_slice():
    # the same loop with str instead of bytes, as the control that cancels the
    # interpreter overhead of the loop itself
    s = TEXT
    for _ in repeat(None, N):
        s[:4]


def report(name, fn):
    best = 0.0
    for _ in range(ROUNDS):
        start = time.perf_counter()
        fn()
        elapsed = time.perf_counter() - start
        best = max(best, N / elapsed)
    print(f"{name:28s} {best:14,.0f} ops/s")


report("bytes encode", shape_encode)
report("bytes slice", shape_slice)
report("bytes() from bytes", shape_ctor)
report("bytes join", shape_join)
report("str slice (control)", shape_str_slice)
