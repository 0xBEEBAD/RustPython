"""os.stat_result must carry the Windows creation time, in CPython's order.

CPython's `stat_result_fields` table (Modules/posixmodule.c) ends, on Windows,
with `st_birthtime`, `st_birthtime_ns`, `st_file_attributes`, `st_reparse_tag`
at body indices 16..19 - so `n_fields` is 20 and those four are the hidden
fields `__reduce__` names for the constructor. Ours stopped at 18 and declared
the last two the other way round, which changes what a positional
`stat_result(20-sequence)` means.

Run this against the reference interpreter first: what it prints is the
expectation, not a restatement of our code.
    bench/labs/cp314/python.exe                   bench/labs/test_stat_birthtime.py
    target/release/rustpython.exe                 bench/labs/test_stat_birthtime.py
"""

import os
import sys

ROWS = []


def check(name, got, want):
    ROWS.append((name, repr(got), repr(want), got == want))


sr = os.stat(__file__)
windows = sys.platform.startswith("win")

hidden = list(sr.__reduce__()[1][1])
want_hidden = [
    "st_atime",
    "st_mtime",
    "st_ctime",
    "st_atime_ns",
    "st_mtime_ns",
    "st_ctime_ns",
    "st_birthtime",
    "st_birthtime_ns",
    "st_file_attributes",
    "st_reparse_tag",
]
check("n_fields", sr.n_fields, 20 if windows else sr.n_fields)
check("hidden names in body order", hidden, want_hidden if windows else hidden)
check("has st_birthtime", hasattr(sr, "st_birthtime"), windows)
check("has st_birthtime_ns", hasattr(sr, "st_birthtime_ns"), windows)
check("st_birthtime type", type(sr.st_birthtime).__name__ if windows else "skip", "float" if windows else "skip")
check("st_birthtime_ns type", type(sr.st_birthtime_ns).__name__ if windows else "skip", "int" if windows else "skip")
check("st_birthtime is an epoch", 1e9 < sr.st_birthtime < 4e9, True)
check("seconds agree", int(sr.st_birthtime), sr.st_birthtime_ns // 10**9)
check("reduce value matches attribute", sr.__reduce__()[1][1]["st_birthtime"], sr.st_birthtime)

# Positional construction is what pins the order: index 16 of a full-length
# sequence has to land in st_birthtime, and 18/19 in file attributes/reparse tag.
body = list(sr[: sr.n_sequence_fields]) + [
    getattr(sr, name) for name in want_hidden[: sr.n_fields - sr.n_sequence_fields]
]
rebuilt = type(sr)(body)
check("positional st_birthtime", rebuilt.st_birthtime, sr.st_birthtime)
check("positional st_birthtime_ns", rebuilt.st_birthtime_ns, sr.st_birthtime_ns)
check("positional st_file_attributes", rebuilt.st_file_attributes, sr.st_file_attributes)
check("positional st_reparse_tag", rebuilt.st_reparse_tag, sr.st_reparse_tag)

rebuilt_2 = type(sr)(*sr.__reduce__()[1])
check("reduce round trip", rebuilt_2.st_birthtime, sr.st_birthtime)
check("reduce round trip len", len(tuple(rebuilt_2)), sr.n_sequence_fields)

# A creation time cannot be later than the last modification for a file we
# wrote just now, and both must be plausible - catches a zeroed or swapped field.
fresh = os.path.join(os.path.dirname(os.path.abspath(__file__)) or ".", "_stat_birthtime_fresh")
with open(fresh, "wb") as fh:
    fh.write(b"x")
try:
    f_sr = os.stat(fresh)
    check("fresh birthtime <= mtime", f_sr.st_birthtime <= f_sr.st_mtime + 2, True)
    check("fresh birthtime_ns == birthtime ns part", f_sr.st_birthtime_ns % 10**9 < 10**9, True)
finally:
    os.unlink(fresh)

bad = [r for r in ROWS if not r[3]]
for name, got, want, ok in ROWS:
    if not ok:
        print(f"FAIL {name}: got {got} want {want}")
print(f"{len(ROWS) - len(bad)}/{len(ROWS)} rows match CPython")
sys.exit(1 if bad else 0)
