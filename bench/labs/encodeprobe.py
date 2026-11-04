"""Where the 600 ns of `s.encode()` lives: registry lookup, or the encoder call?

CPython answers a default `str.encode()` from C in ~34 ns for an 8-char ASCII
string; this fork takes ~634 ns. The candidate costs are the codec registry
round trip (name normalization, lock, hash, clone, `_is_text_encoding` probe)
and the Python-level call into `codecs.utf_8_encode` that follows it, so each
row keeps one of them and drops the other.

    python bench/labs/encodeprobe.py
"""

import codecs
import timeit

N = 50_000
s = "abcdefgh"
empty = ""
long = "abcdefgh" * 100
lookup = codecs.lookup
enc = codecs.lookup("utf-8")

SHAPES = [
    ("lambda baseline", lambda: None),
    ("s.upper() control", lambda: s.upper()),
    ("s.encode()", lambda: s.encode()),
    ("s.encode('utf-8')", lambda: s.encode("utf-8")),
    ("s.encode('utf8')", lambda: s.encode("utf8")),
    ("s.encode('ascii')", lambda: s.encode("ascii")),
    ("s.encode('latin-1')", lambda: s.encode("latin-1")),
    ("''.encode()", lambda: empty.encode()),
    ("s*100 .encode()", lambda: long.encode()),
    ("lookup('utf-8')", lambda: lookup("utf-8")),
    ("enc.encode(s)[0]", lambda: enc.encode(s)[0]),
    ("codecs.encode(s)", lambda: codecs.encode(s, "utf-8")),
    ("bytes(s,'utf-8')", lambda: bytes(s, "utf-8")),
    ("b'x'*8 .decode()", lambda: b"abcdefgh".decode()),
    ("s.encode(errors='strict')", lambda: s.encode(errors="strict")),
    ("s.isascii() control", lambda: s.isascii()),
]

for name, fn in SHAPES:
    best = min(timeit.repeat(fn, number=N, repeat=3))
    print(f"{name:32s} {best / N * 1e9:7.1f} ns/iter")
