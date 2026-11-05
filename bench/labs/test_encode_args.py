"""`str.encode` / `bytes.decode` / `bytearray.decode` argument parity (task #90).

CPython validates these two parameters through Argument Clinic's `str` converter,
which means: absent is the default, an explicit `None` is a *type error*, and the
rejection names the function and the parameter
(`Objects/clinic/unicodeobject.c.h` calls
`_PyArg_BadArgument("encode", "argument 'encoding'", "str", args[0])`, which
formats `"%.200s() %.200s must be %.50s, not %.50s"` with `None` spelled `None`
- `Python/getargs.c`). The fork bound both as `Option<PyUtf8StrRef>`, so `None`
silently meant "use the default" and a wrong type produced the generic binding
message.

Every expectation below is copied from what the reference interpreter prints for
the same call, so running this file under `bench/labs/cp314/python.exe` proves the
table is faithful, and running it under rustpython proves the behaviour.

    bench/labs/cp314/python.exe       bench/labs/test_encode_args.py
    target/release/rustpython.exe     bench/labs/test_encode_args.py
"""

import codecs as _codecs
import sys

failures = []


def enc(fn, typ):
    return f"TypeError: {fn}() argument 'encoding' must be str, not {typ}"


def err(fn, typ):
    return f"TypeError: {fn}() argument 'errors' must be str, not {typ}"


CASES = [
    # (label, thunk, expected rendering)
    ("s.encode()", lambda: "abc".encode(), "ok: b'abc'"),
    ("s.encode(None)", lambda: "abc".encode(None), enc("encode", "None")),
    ("s.encode(encoding=None)", lambda: "abc".encode(encoding=None), enc("encode", "None")),
    ("s.encode(errors=None)", lambda: "abc".encode(errors=None), err("encode", "None")),
    ("s.encode('utf-8', None)", lambda: "abc".encode("utf-8", None), err("encode", "None")),
    ("s.encode(1)", lambda: "abc".encode(1), enc("encode", "int")),
    ("s.encode(encoding=1)", lambda: "abc".encode(encoding=1), enc("encode", "int")),
    ("s.encode(errors=1)", lambda: "abc".encode(errors=1), err("encode", "int")),
    ("s.encode(None, None)", lambda: "abc".encode(None, None), enc("encode", "None")),
    ("s.encode(b'utf-8')", lambda: "abc".encode(b"utf-8"), enc("encode", "bytes")),
    ("b.decode(None)", lambda: b"abc".decode(None), enc("decode", "None")),
    ("b.decode(encoding=None)", lambda: b"abc".decode(encoding=None), enc("decode", "None")),
    ("b.decode(errors=None)", lambda: b"abc".decode(errors=None), err("decode", "None")),
    ("b.decode(1)", lambda: b"abc".decode(1), enc("decode", "int")),
    ("b.decode(errors=1)", lambda: b"abc".decode(errors=1), err("decode", "int")),
    ("b.decode('utf-8', None)", lambda: b"abc".decode("utf-8", None), err("decode", "None")),
    ("ba.decode(None)", lambda: bytearray(b"abc").decode(None), enc("decode", "None")),
    ("ba.decode(errors=None)", lambda: bytearray(b"abc").decode(errors=None), err("decode", "None")),
    # codecs.encode / codecs.decode run through the same clinic converter, so
    # they reject None the same way and name themselves, not the methods.
    (
        "codecs.encode('abc', None)",
        lambda: _codecs.encode("abc", None),
        enc("encode", "None"),
    ),
    (
        "codecs.encode('abc', encoding=None)",
        lambda: _codecs.encode("abc", encoding=None),
        enc("encode", "None"),
    ),
    (
        "codecs.encode('abc', errors=None)",
        lambda: _codecs.encode("abc", errors=None),
        err("encode", "None"),
    ),
    (
        "codecs.encode('abc', 'utf-8', None)",
        lambda: _codecs.encode("abc", "utf-8", None),
        err("encode", "None"),
    ),
    ("codecs.encode('abc', 1)", lambda: _codecs.encode("abc", 1), enc("encode", "int")),
    (
        "codecs.decode(b'abc', None)",
        lambda: _codecs.decode(b"abc", None),
        enc("decode", "None"),
    ),
    (
        "codecs.decode(b'abc', encoding=None)",
        lambda: _codecs.decode(b"abc", encoding=None),
        enc("decode", "None"),
    ),
    (
        "codecs.decode(b'abc', errors=None)",
        lambda: _codecs.decode(b"abc", errors=None),
        err("decode", "None"),
    ),
    (
        "codecs.decode(b'abc', 'utf-8', None)",
        lambda: _codecs.decode(b"abc", "utf-8", None),
        err("decode", "None"),
    ),
    ("codecs.encode('abc')", lambda: _codecs.encode("abc"), "ok: b'abc'"),
    ("codecs.decode(b'abc')", lambda: _codecs.decode(b"abc"), "ok: 'abc'"),
    # Controls that must keep passing: an unknown *handler* name is not looked up
    # until an error actually happens, so it is accepted, and the LookupError for
    # an unknown codec has to name it exactly as it was written, not normalized.
    ("s.encode(errors='unknown')", lambda: "abc".encode(errors="unknown"), "ok: b'abc'"),
    ("s.encode('utf-8')", lambda: "abc".encode("utf-8"), "ok: b'abc'"),
    (
        "s.encode('unknown-codec')",
        lambda: "abc".encode("unknown-codec"),
        "LookupError: unknown encoding: unknown-codec",
    ),
    (
        "b.decode('unknown-codec')",
        lambda: b"abc".decode("unknown-codec"),
        "LookupError: unknown encoding: unknown-codec",
    ),
    ("b.decode()", lambda: b"abc".decode(), "ok: 'abc'"),
    ("ba.decode()", lambda: bytearray(b"abc").decode(), "ok: 'abc'"),
]


def render(thunk):
    try:
        value = thunk()
    except BaseException as exc:  # noqa: BLE001 - the message is the subject
        return f"{type(exc).__name__}: {exc}"
    return f"ok: {value!r}"


for label, thunk, expected in CASES:
    actual = render(thunk)
    if actual != expected:
        failures.append(f"{label}\n    want {expected}\n    got  {actual}")

print(f"codec argument parity: {len(CASES) - len(failures)}/{len(CASES)}",
      "PASS" if not failures else "FAIL")
for line in failures:
    print("  FAIL", line)
sys.exit(1 if failures else 0)
