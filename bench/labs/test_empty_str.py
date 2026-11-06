"""Every empty str a builtin produces must be the one immortal singleton.

CPython routes zero-length results through `_PyUnicode_GetEmpty()` inside
`PyUnicode_New` itself (Objects/unicodeobject.c:1281), so *no* code path can
make a second empty string. Our `PyStr` construction allocates a husk for
length 0 instead, which costs a whole string lifecycle per empty piece and is
visible from Python as an identity difference.

These rows are the shape of the gap, measured side by side:

    bench/labs/cp314/python.exe                bench/labs/test_empty_str.py
    target/release/rustpython.exe              bench/labs/test_empty_str.py

`is ''` on a literal warns; comparing against a bound name keeps the check
honest and quiet.
"""

import sys

EMPTY = ""
failures = []


def check(label, got, want):
    if got != want:
        failures.append(label)
    print(f"{'ok  ' if got == want else 'FAIL'} {label:32s} got {got!r} want {want!r}")


# the singleton itself
check("literal is the singleton", "" is EMPTY, True)
check("str() is the singleton", str() is EMPTY, True)

# pieces of splits and partitions - the common hot case
check("split middle empty", "a,,b".split(",")[1] is EMPTY, True)
check("split leading empty", ",ab".split(",")[0] is EMPTY, True)
check("split trailing empty", "ab,".split(",")[-1] is EMPTY, True)
check("partition empty pieces", "abc".partition("abc")[0] is EMPTY, True)
check("rpartition empty tail", "abc".rpartition("abc")[2] is EMPTY, True)
check("rsplit empty", ",a".rsplit(",")[0] is EMPTY, True)
check("splitlines on empty", "".splitlines(), [])
check("maxsplit keeps the remainder", "a,,b".split(",", 1)[1] == ",b", True)

# other producers of empty strings
check("join of nothing", "".join([]) is EMPTY, True)
check("join of empties", "".join(["", ""]) is EMPTY, True)
check("upper of empty", EMPTY.upper() is EMPTY, True)
check("casefold of empty", EMPTY.casefold() is EMPTY, True)
check("strip of empty", EMPTY.strip() is EMPTY, True)
check("replace that changes nothing", "abc".replace("z", "") is not EMPTY, True)
check("empty slice", ("abc"[:0]) is EMPTY, True)
check("encode of empty", EMPTY.encode() is b"", True)
check("format with no fields", "{}".format(EMPTY) is EMPTY, True)

# values must still be right, not just shared
check("split values", "a,,b".split(","), ["a", "", "b"])
check("partition values", "abc".partition("abc"), ("", "abc", ""))
check("empty length", len(EMPTY), 0)
check("empty hash", hash(EMPTY), hash(""[:0]))

ROWS = 23
print(f"{len(failures)} failures of {ROWS} rows")
sys.exit(1 if failures else 0)
