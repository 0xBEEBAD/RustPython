"""Pattern.prefixmatch is CPython 3.15's real name, and `match` is its alias.

3.15's clinic block is `_sre.SRE_Pattern.prefixmatch(string, pos=0,
endpos=sys.maxsize)` (Modules/_sre/sre.c:770) and the comment at
Modules/_sre/sre.c:3166 says "match reuses the prefixmatch Clinic-generated
parser and impl". The reference binary here is 3.14.7, which has no
`prefixmatch` at all, so the oracle is the 3.15 source plus the requirement
that the two names answer identically - which is what the alias means.

    bench/labs/variants/rp-lite-slimstr.exe              bench/labs/test_prefixmatch.py   # red
    target/release/rustpython.exe                        bench/labs/test_prefixmatch.py   # green
"""

import re
import sys

failures = []


def check(label, got, want):
    ok = got == want
    if not ok:
        failures.append(label)
    print(f"{'ok  ' if ok else 'FAIL'} {label:42s} got {got!r} want {want!r}")


p = re.compile(r"\w+(?:\.\w+)*")

# the names must both exist, on Pattern and on the scanner
check("Pattern.prefixmatch exists", hasattr(p, "prefixmatch"), True)
check("Pattern.match exists", hasattr(p, "match"), True)
scanner = p.scanner("abc.def")
check("Scanner.prefixmatch exists", hasattr(scanner, "prefixmatch"), True)

# the alias must answer exactly what `match` answers, for every argument shape
cases = [
    ("  abc.def[", (), {}),
    ("abc.def", (), {}),
    ("zz abc", (3,), {}),
    ("zz abc", (), {"pos": 3}),
    ("abc.def", (), {"endpos": 3}),
    ("abc.def", (0, 3), {}),
    ("", (), {}),
    ("  ", (), {}),
]
for string, args, kwargs in cases:
    key = f"{string!r}{args}{kwargs}"
    via_match = p.match(string, *args, **kwargs)
    via_prefix = p.prefixmatch(string, *args, **kwargs)
    check(
        f"prefixmatch == match {key}",
        (via_prefix.span(), via_prefix.group()) if via_prefix else None,
        (via_match.span(), via_match.group()) if via_match else None,
    )

# prefix anchoring only: nothing at position 0 means nothing, wherever it is
check("prefixmatch does not search ahead", p.prefixmatch("!!!abc"), None)
check("search still finds it later", p.search("!!!abc").span(), (3, 6))

# bytes patterns go through the same entry point
bp = re.compile(rb"\d+")
check("bytes prefixmatch", bp.prefixmatch(b"12ab").group(), bp.match(b"12ab").group())

# errors are the same errors `match` raises
for bad in (5, None):
    try:
        p.prefixmatch(bad)
        check(f"prefixmatch({type(bad).__name__}) raises", "no raise", "TypeError")
    except TypeError as exc:
        try:
            p.match(bad)
            want = str(exc)
        except TypeError as other:
            want = str(other)
        check(f"prefixmatch({type(bad).__name__}) says what match says", str(exc), want)

# dataclasses.py is the stdlib caller this unblocks: `_is_type` resolves a
# *string* ClassVar/InitVar annotation through prefixmatch, so a dataclass with
# string annotations is the honest witness that the alias really works.
from dataclasses import InitVar, dataclass, fields  # noqa: E402
# _is_type resolves the root of a string annotation out of *this module*, so the
# names have to be importable here or the rows below fail for the wrong reason.
# `InitVar` lives in dataclasses and `ClassVar` in typing - neither is in the
# other, on 3.14.7 and here alike (checked, not assumed).
from typing import ClassVar  # noqa: E402,F401


@dataclass
class UsesStringAnnotations:
    cv: "ClassVar[int]" = 0
    iv: "InitVar[int]" = 0
    value: "int" = 0

    def __post_init__(self, iv):
        self.total = iv + self.value


# `fields()` reports real fields only - a ClassVar is not a field and an
# InitVar is a pseudo-field - which is ['value'] on both interpreters, checked.
check(
    "string ClassVar and InitVar left fields()",
    [f.name for f in fields(UsesStringAnnotations)],
    ["value"],
)
check("string InitVar became an init argument", UsesStringAnnotations(20, 3).total, 23)

print(f"{len(failures)} failures out of the rows above")
sys.exit(1 if failures else 0)
