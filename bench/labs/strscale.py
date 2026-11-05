"""Does building a string object cost scale with the bytes, or is it fixed?

Task #93 measured one string object's lifecycle at ~48-63 ns and proved it is
construction, not allocation or destruction. Two explanations are left, and they
need different fixes:

  * per-byte work - `SsoBuf::new` zero-fills 22 bytes then copies the payload, and
    `StrData::try_sso` re-derives the kind and the char count from bytes whose
    caller already knows they are ASCII. Cost grows with length.
  * per-object work - the header write in `into_ref` (refcount, type, payload
    move, GC/weakref prefix). Cost is flat with length.

`str.split` on a string of fixed-length pieces builds exactly one string per piece
and nothing else, so timing it across piece lengths separates the two. Piece
length 1 is excluded because single characters answer from the Latin-1 singleton
cache and never construct anything.

    target/release/rustpython.exe bench/labs/strscale.py
    bench/labs/cp314/python.exe bench/labs/strscale.py   # reference for shape only
"""

import time

N = 200_000
REPS = 7


def measure(length):
    # N pieces of exactly `length` bytes, joined by a separator that is itself a
    # single byte, so the receiver is one byte longer per piece than the payload.
    piece = "a" * length
    source = ",".join([piece] * N)
    best = float("inf")
    for _ in range(REPS):
        start = time.perf_counter()
        result = source.split(",")
        elapsed = time.perf_counter() - start
        best = min(best, elapsed)
    del result
    return best / N * 1e9


print("== per-piece ns by piece length (min of %d runs, %d pieces)" % (REPS, N))
rows = []
for length in (2, 4, 8, 12, 20, 22, 24, 40):
    ns = measure(length)
    rows.append((length, ns))
    print(f"piece_len={length:3d}  {ns:7.1f} ns/piece")

short = sum(ns for length, ns in rows if length <= 12) / 4
long_side = sum(ns for length, ns in rows if length >= 24) / 2
print(
    f"slope signal: len<=12 {short:.1f} ns vs len>=24 {long_side:.1f} ns "
    f"(flat means the cost is the object header, not the bytes)"
)
