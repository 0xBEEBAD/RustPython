"""Values produced by the ASCII-known string constructor, and its ablate twin.

`StrData::from_known_ascii` (used by every ASCII piece `str.split` produces)
skips the kind/character-count derivation that `StrData::try_sso` performs. Both
routes must therefore agree on *everything a program can observe* - the value,
the length, the hash, what `repr` prints, and which strings the interpreter hands
back from its caches - so this file is run twice on one binary, once with
`LUNA_ABLATE=strascii` (the old deriving route) and once without, and the two
outputs must match byte-for-byte.

Lengths straddle the 22-byte SSO capacity, because the two storage classes are
built by different code inside the constructor.

    bench/labs/cp314/python.py             this file   # reference values
    target/release/rustpython.exe          this file
    LUNA_ABLATE=strascii target/release/rustpython.exe this file
"""

import sys

failures = []


def check(name, cond, detail=""):
    if not cond:
        failures.append(f"{name}: {detail}")


SSO = 22
# A receiver of fixed-length ASCII pieces, split apart again: this is the only
# public surface that reaches the constructor under test.
for length in (1, 2, 3, 8, 21, 22, 23, 24, 40, 64):
    piece = "a" * length
    source = ",".join([piece, piece, piece])
    parts = source.split(",")
    check(f"len={length} count", len(parts) == 3, len(parts))
    for part in parts:
        check(f"len={length} value", part == piece, repr(part))
        check(f"len={length} str len", len(part) == length, len(part))
        # The hash must equal the hash of the same characters built another way,
        # or dict lookups and interning would silently diverge.
        check(f"len={length} hash", hash(part) == hash(piece), length)
    check(f"len={length} dict key", {piece: 1}[parts[0]] == 1, length)
    check(f"len={length} upper", parts[0].upper() == "A" * length, parts[0].upper())
    check(f"len={length} repr", repr(parts[0]) == repr(piece), repr(parts[0]))

# Mixed-case and digit ASCII, so the constructor is not only ever fed 'a'.
mixed = "Zz09!~_-.,'\"/\\<>="
check("mixed split", mixed.split("!") == ["Zz09", "~_-.,'\"/\\<>="], mixed.split("!"))
check("mixed len", len(mixed.split("!")[0]) == 4, mixed.split("!")[0])

# Non-ASCII must be untouched by an ASCII-only shortcut: the same receiver built
# with a multibyte payload goes through the deriving route, and its length is in
# characters, not bytes.
for text in ("é" * 5, "日本" * 3, "\U0001f600abc", "aé b"):
    parts = ("x," + text).split(",")
    check(f"nonascii value {len(text)}", parts[1] == text, repr(parts[1]))
    check(f"nonascii len {len(text)}", len(parts[1]) == len(text), len(parts[1]))
    check(f"nonascii hash {len(text)}", hash(parts[1]) == hash(text), len(text))

# Empty and single-character pieces still answer from their own paths.
check("empty piece", "a,,b".split(",") == ["a", "", "b"], "a,,b".split(","))
check("char cache", "q,q".split(",")[0] == "q", "q,q".split(","))

print("known-ascii parity:", "PASS" if not failures else "FAIL")
print("checks failed:", len(failures))
for line in failures:
    print("  FAIL", line)
sys.exit(1 if failures else 0)
