"""Print the exact TypeError each interpreter raises for bad `str.encode` /
`bytes.decode` arguments, so the messages can be pinned from measurement.

CPython validates these through C converters, which reject `None` for the
encoding but accept `None` for `errors` (meaning "strict"). Whether this fork's
`Option<PyUtf8StrRef>` binding reproduces that asymmetry is what task #90 asks.

    bench/labs/cp314/python.exe bench/labs/encodeargvalues.py
    target/release/rustpython.exe bench/labs/encodeargvalues.py
"""


def show(label, fn):
    try:
        value = fn()
    except BaseException as e:  # noqa: BLE001 - the probe reports the message
        print(f"{label:34s} {type(e).__name__}: {e}")
        return
    print(f"{label:34s} ok: {value!r}")


s = "abc"
b = b"abc"

show("s.encode(None)", lambda: s.encode(None))
show("s.encode(encoding=None)", lambda: s.encode(encoding=None))
show("s.encode(errors=None)", lambda: s.encode(errors=None))
show("s.encode('utf-8', None)", lambda: s.encode("utf-8", None))
show("s.encode(1)", lambda: s.encode(1))
show("s.encode(encoding=1)", lambda: s.encode(encoding=1))
show("s.encode(errors=1)", lambda: s.encode(errors=1))
show("s.encode(None, None)", lambda: s.encode(None, None))
show("s.encode(b'utf-8')", lambda: s.encode(b"utf-8"))
show("b.decode(None)", lambda: b.decode(None))
show("b.decode(encoding=None)", lambda: b.decode(encoding=None))
show("b.decode(errors=None)", lambda: b.decode(errors=None))
show("b.decode(1)", lambda: b.decode(1))
show("b.decode(errors=1)", lambda: b.decode(errors=1))
show("b.decode('utf-8', None)", lambda: b.decode("utf-8", None))
show("bytearray(b'abc').decode(None)", lambda: bytearray(b"abc").decode(None))
show("bytearray(b'abc').decode(errors=None)", lambda: bytearray(b"abc").decode(errors=None))
show("s.encode('utf-8')", lambda: s.encode("utf-8"))
show("s.encode('unknown-codec')", lambda: s.encode("unknown-codec"))
show("s.encode(errors='unknown')", lambda: s.encode(errors="unknown"))
show("b.decode('unknown-codec')", lambda: b.decode("unknown-codec"))

# The same clinic converter guards the constructors, the module-level codec
# functions and codecs.lookup's message, so measure those too instead of
# assuming they agree with the two methods above. `open(encoding=None)` is the
# deliberate opposite case: there None really does mean "locale default".
import codecs  # noqa: E402

show("codecs.lookup('unknown-codec')", lambda: codecs.lookup("unknown-codec"))
show("str('abc', None)", lambda: str("abc", None))
show("str('abc', 'utf-8', None)", lambda: str("abc", "utf-8", None))
show("str('abc', errors=None)", lambda: str("abc", errors=None))
show("bytes('abc', None)", lambda: bytes("abc", None))
show("bytes('abc', 'utf-8', None)", lambda: bytes("abc", "utf-8", None))
show("bytearray('abc', None)", lambda: bytearray("abc", None))
show("bytearray('abc', errors=None)", lambda: bytearray("abc", errors=None))
show("codecs.encode('abc', None)", lambda: codecs.encode("abc", None))
show("codecs.encode('abc', 'utf-8', None)", lambda: codecs.encode("abc", "utf-8", None))
show("codecs.decode(b'abc', None)", lambda: codecs.decode(b"abc", None))
show("open(encoding=None, errors=None)", lambda: open(
    "bench/labs/encodeargvalues.py", encoding=None, errors=None).read(2))

# Measured on the reference: for `str()` the POSITIONAL form reports `NoneType`
# while the KEYWORD form reports `None`, so the split may be by *how* the
# argument was passed rather than by which parameter it is. Map both paths for
# every entry point before writing any message.
show("str('abc', encoding=None)", lambda: str("abc", encoding=None))
show("bytes('abc', encoding=None)", lambda: bytes("abc", encoding=None))
show("bytes('abc', errors=None)", lambda: bytes("abc", errors=None))
show("bytearray('abc', encoding=None)", lambda: bytearray("abc", encoding=None))
show("codecs.encode('abc', encoding=None)", lambda: codecs.encode("abc", encoding=None))
show("codecs.encode('abc', errors=None)", lambda: codecs.encode("abc", errors=None))
show("codecs.decode(b'abc', encoding=None)", lambda: codecs.decode(b"abc", encoding=None))
show("codecs.decode(b'abc', errors=None)", lambda: codecs.decode(b"abc", errors=None))
show("codecs.decode(b'abc', 'utf-8', None)", lambda: codecs.decode(b"abc", "utf-8", None))
show("str('abc', 1)", lambda: str("abc", 1))
show("bytes('abc', 1)", lambda: bytes("abc", 1))
show("codecs.encode('abc', 1)", lambda: codecs.encode("abc", 1))
