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
