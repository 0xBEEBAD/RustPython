"""Pin CPython's two different builtin-call error names.

Measured on CPython 3.14.7: the `takes no keyword arguments` rejection uses the
method's *qualified* name (`str.count()`, `tuple.index()`, `dict.keys()`), while
the `got an unexpected keyword argument` rejection uses the *bare* name
(`split()`, `to_bytes()`, `hex()`). The two messages come from different paths in
CPython's argument parsing, so a fix that makes one right can make the other
wrong - which is why both families are pinned here, and why each case is run in
both the bound (`'a'.count(...)`) and unbound (`str.count('a', ...)`) form: the
interpreter reaches the same callee through a different object for each.

Expected strings are CPython's own, so this file is a parity test, not a
description of what RustPython currently does.

    python bench/labs/test_kwmsg.py
"""

import sys

# (expression, expected TypeError message) - measured on CPython 3.14.7
QUALIFIED = [
    ("'a'.count(overlapping=True)", "str.count() takes no keyword arguments"),
    ("str.count('a', overlapping=True)", "str.count() takes no keyword arguments"),
    ("'a'.upper(x=1)", "str.upper() takes no keyword arguments"),
    ("str.upper('a', x=1)", "str.upper() takes no keyword arguments"),
    ("().index(x=2)", "tuple.index() takes no keyword arguments"),
    ("tuple.index((), x=2)", "tuple.index() takes no keyword arguments"),
    ("{}.keys(x=2)", "dict.keys() takes no keyword arguments"),
    ("{}.pop(k=1)", "dict.pop() takes no keyword arguments"),
    ("[].append(1, item=2)", "list.append() takes no keyword arguments"),
    ("list.append([], 1, item=2)", "list.append() takes no keyword arguments"),
    ("'a'.join(x=1)", "str.join() takes no keyword arguments"),
    (
        "frozenset({1}).isdisjoint(x=1)",
        "frozenset.isdisjoint() takes no keyword arguments",
    ),
    ("(1.5).hex(x=1)", "float.hex() takes no keyword arguments"),
    ("'a'.startswith(x=1)", "str.startswith() takes no keyword arguments"),
]

BARE = [
    ("'a'.split(maxsplt=1)", "split() got an unexpected keyword argument 'maxsplt'"),
    (
        "str.split('a', maxsplt=1)",
        "split() got an unexpected keyword argument 'maxsplt'",
    ),
    (
        "(1).to_bytes(x=1)",
        "to_bytes() got an unexpected keyword argument 'x'",
    ),
    (
        "int.to_bytes(1, x=1)",
        "to_bytes() got an unexpected keyword argument 'x'",
    ),
    ("b''.hex(x=1)", "hex() got an unexpected keyword argument 'x'"),
    # A builtin *function* has no class, so it keeps the plain name in both.
    ("len('a', x=1)", "len() takes no keyword arguments"),
]

failures = 0
for group, cases in (("qualified", QUALIFIED), ("bare", BARE)):
    for text, expected in cases:
        try:
            eval(text, {}, {})
            got = "NO ERROR"
        except TypeError as exc:
            # CPython appends a "Did you mean" hint for a near-miss name; compare
            # only the part the interpreter builds itself.
            got = str(exc).split(". Did you mean")[0]
        except Exception as exc:  # noqa: BLE001 - any other error is a mismatch too
            got = f"{type(exc).__name__}: {exc}"
        if got != expected:
            failures += 1
            print(f"FAIL [{group}] {text}\n     want {expected!r}\n     got  {got!r}")

print(
    f"{'OK' if failures == 0 else 'FAILED'}: {len(QUALIFIED) + len(BARE)} cases, "
    f"{failures} mismatched on {sys.implementation.name} {sys.version_info[:3]}"
)
sys.exit(1 if failures else 0)
