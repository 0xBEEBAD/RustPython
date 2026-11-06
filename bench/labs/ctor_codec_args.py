"""Print, not assert, what each codec-argument shape does.

Run this on the reference interpreter and on RustPython and diff the two
outputs; every differing line is a parity defect. Writing the expectation down
by hand would only restate what we already believe, so the table is the
evidence and the diff is the test.

    bench/labs/cp314/python.exe                            bench/labs/ctor_codec_args.py > temp/ctor-cp.txt
    target/release/rustpython.exe                          bench/labs/ctor_codec_args.py > temp/ctor-rp.txt
    diff temp/ctor-cp.txt temp/ctor-rp.txt

`bytes.__new__`, `bytearray.__new__` and `str.__new__` take encoding/errors
through their own argument structs, separate from the `encode`/`decode` paths
that CodecArg already covers, so they need their own rows.
"""

import sys

CASES = []


def case(label, fn):
    CASES.append((label, fn))


# --- bytes(b'...', encoding, errors): the shape is (object, encoding, errors)
case("bytes/absent", lambda: bytes("abc", "utf-8"))
case("bytes/enc-none-pos", lambda: bytes("abc", None))
case("bytes/enc-none-kw", lambda: bytes("abc", encoding=None))
case("bytes/err-none-pos", lambda: bytes("abc", "utf-8", None))
case("bytes/err-none-kw", lambda: bytes("abc", "utf-8", errors=None))
case("bytes/enc-int-pos", lambda: bytes("abc", 1))
case("bytes/enc-int-kw", lambda: bytes("abc", encoding=1))
case("bytes/err-int-kw", lambda: bytes("abc", "utf-8", errors=1))
case("bytes/enc-bytes-kw", lambda: bytes("abc", encoding=b"utf-8"))
case("bytes/no-args", lambda: bytes())
case("bytes/int", lambda: bytes(3))
case("bytes/str-no-enc", lambda: bytes("abc"))
case("bytes/enc-kw-only", lambda: bytes("abc", errors="strict"))

# --- bytearray shares the constructor argument struct
case("bytearray/enc-none-pos", lambda: bytearray("abc", None))
case("bytearray/enc-none-kw", lambda: bytearray("abc", encoding=None))
case("bytearray/err-none-kw", lambda: bytearray("abc", "utf-8", errors=None))
case("bytearray/enc-int-kw", lambda: bytearray("abc", encoding=1))
case("bytearray/str-no-enc", lambda: bytearray("abc"))

# --- str(object, encoding, errors)
case("str/absent", lambda: str(b"abc", "utf-8"))
case("str/enc-none-pos", lambda: str(b"abc", None))
case("str/enc-none-kw", lambda: str(b"abc", encoding=None))
case("str/err-none-pos", lambda: str(b"abc", "utf-8", None))
case("str/err-none-kw", lambda: str(b"abc", "utf-8", errors=None))
case("str/enc-int-pos", lambda: str(b"abc", 1))
case("str/enc-int-kw", lambda: str(b"abc", encoding=1))
case("str/err-int-kw", lambda: str(b"abc", "utf-8", errors=1))
case("str/both-kw", lambda: str(b"abc", encoding="utf-8", errors="strict"))
case("str/both-int-pos", lambda: str(b"abc", 1, 2))
case("str/err-int-pos", lambda: str(b"abc", "utf-8", 2))
case("str/int-with-enc", lambda: str(1, "utf-8"))
case("str/none-with-enc", lambda: str(None, "utf-8"))
case("str/obj-and-enc-kw", lambda: str(1, encoding="utf-8"))
case("bytes/int-with-enc", lambda: bytes(1, "utf-8"))
case("bytes/none-with-enc", lambda: bytes(None, "utf-8"))
case("bytes/both-int-pos", lambda: bytes("abc", 1, 2))
case("str/no-args", lambda: str())
case("str/obj-only", lambda: str(123))
case("str/enc-kw-only", lambda: str(b"abc", errors="strict"))

# --- codecs.encode/decode keep the landed behaviour in the same view
case("codecs/encode-enc-none-kw", lambda: __import__("codecs").encode("abc", errors=None))
case("codecs/decode-enc-none-kw", lambda: __import__("codecs").decode(b"abc", errors=None))

for label, fn in CASES:
    try:
        value = fn()
        if isinstance(value, (bytes, bytearray)) and len(value) > 24:
            value = value[:24]
        print(f"{label:28s} ok      {value!r}")
    except BaseException as exc:
        print(f"{label:28s} {type(exc).__name__:<14s} {exc}")

print(f"# {len(CASES)} rows, {sys.version_info[:2]}")
