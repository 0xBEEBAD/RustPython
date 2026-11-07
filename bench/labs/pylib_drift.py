"""Rank the remaining CPython 3.15 library drift by how little work it is.

`scripts/update_lib todo` is not usable for this: its up-to-date test compares
bytes while its delta column compares text, so on a CRLF checkout a synced
module is reported pending forever (task #111), and it has no way to express a
divergence this fork keeps on purpose. This measures the thing directly: for
each top-level stdlib module, how many lines differ from the 3.15 tree, and does
the file carry a RUSTPYTHON marker, which is the signal that some of the diff is
ours rather than lag.

    bench/labs/cp314/python.exe bench/labs/pylib_drift.py

It only counts, it does not judge: a big number can be a comment reflow and a
small one can be a missing feature. The point is an ordered queue for
`upgrade-pylib` that is derived from the files instead of from the tool.
"""

import difflib
import os
import sys

CP315 = r"C:\Projects\luna-lang\cpython315-src\cpython-3.15\Lib"
OURS = "Lib"


def main():
    if not os.path.isdir(CP315):
        print("no 3.15 tree at %s" % CP315)
        return 1
    rows = []
    missing = []
    for name in sorted(os.listdir(OURS)):
        path = os.path.join(OURS, name)
        if not os.path.isfile(path) or not name.endswith(".py"):
            continue
        remote = os.path.join(CP315, name)
        if not os.path.isfile(remote):
            missing.append(name)
            continue
        with open(path, encoding="utf-8", errors="replace") as fp:
            mine = fp.read().splitlines()
        with open(remote, encoding="utf-8", errors="replace") as fp:
            theirs = fp.read().splitlines()
        diff = [
            line
            for line in difflib.unified_diff(mine, theirs, n=0)
            if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
        ]
        if diff:
            markers = sum(1 for line in mine if "RUSTPYTHON" in line)
            rows.append((len(diff), markers, name))
    rows.sort()
    print("== %d top-level modules differ from 3.15 ==" % len(rows))
    print("%-28s %8s %8s" % ("module", "diff", "markers"))
    for size, markers, name in rows[:30]:
        print("%-28s %8d %8d" % (name, size, markers))
    print("...")
    for size, markers, name in rows[-8:]:
        print("%-28s %8d %8d" % (name, size, markers))
    total = sum(r[0] for r in rows)
    marked = sum(1 for r in rows if r[1])
    print("total diff lines %d; files with RUSTPYTHON markers %d" % (total, marked))
    if missing:
        print("present here, absent in 3.15: %s" % ", ".join(missing))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
