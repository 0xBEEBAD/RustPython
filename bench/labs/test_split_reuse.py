"""Pin CPython's `split` reuse rule and check it on both interpreters.

CPython reuses the receiver object as the single element when the separator does
not occur (Objects/stringlib/split.h `count == 0 && STRINGLIB_CHECK_EXACT`), and
for `maxsplit == 0`. This fork always allocates a fresh piece, so every
"no-match" row below was red before the fix - and every one of them is both a
parity difference (`is` identity) and an allocation.

    bench/labs/cp314/python.exe          bench/labs/test_split_reuse.py
    target/release/rustpython.exe        bench/labs/test_split_reuse.py
"""


class SubStr(str):
    pass


class SubBytes(bytes):
    pass


CHECKS = []


def check(name, fn):
    CHECKS.append((name, fn))


s = "abc-def"
b = bytes(bytearray(b"abc-def"))
ba = bytearray(b"abc-def")
u = "héllo-wörld"

# exact receivers: the whole object comes back.
check("str no-match reuses", lambda: s.split("z")[0] is s)
check("str no-match value", lambda: s.split("z") == ["abc-def"])
check("str sep longer reuses", lambda: s.split("zzzzzzzz")[0] is s)
check("str maxsplit 0 reuses", lambda: s.split("-", 0)[0] is s)
check("str maxsplit 0 len", lambda: len(s.split("-", 0)) == 1)
check("str maxsplit 5 no-match reuses", lambda: s.split("z", 5)[0] is s)
check("str negative maxsplit reuses", lambda: s.split("z", -1)[0] is s)
check("str rsplit no-match reuses", lambda: s.rsplit("z")[0] is s)
check("str rsplit maxsplit 0 reuses", lambda: s.rsplit("-", 0)[0] is s)
check("str empty receiver reuses", lambda: (lambda e: e.split("z")[0] is e)(""))
check("str keyword sep reuses", lambda: s.split(sep="z")[0] is s)
check("str 2-byte kind no-match reuses", lambda: u.split("z")[0] is u)
check("str 2-byte kind match", lambda: u.split("-") == ["héllo", "wörld"])
check("str non-ascii sep match", lambda: "aéb".split("é") == ["a", "b"])
check("bytes no-match reuses", lambda: b.split(b"z")[0] is b)
check("bytes multi-char sep reuses", lambda: b.split(b"zz")[0] is b)
check("bytes maxsplit 0 reuses", lambda: b.split(b"-", 0)[0] is b)
check("bytes rsplit no-match reuses", lambda: b.rsplit(b"z")[0] is b)

# a matched split never reuses, and the pieces are plain containers.
check("str matched piece is new", lambda: s.split("-")[0] is not s)
check("str matched parts", lambda: s.split("-") == ["abc", "def"])
check("str rsplit matched parts", lambda: s.rsplit("-") == ["abc", "def"])
check("bytes matched piece is new", lambda: b.split(b"-")[0] is not b)
check("bytes matched parts", lambda: b.split(b"-") == [b"abc", b"def"])

# subclasses are not exact: CPython hands back a plain base-type piece.
check("str subclass no-match type", lambda: type(SubStr(s).split("z")[0]) is str)
check("str subclass no-match value", lambda: SubStr(s).split("z")[0] == s)
check("bytes subclass no-match type", lambda: type(SubBytes(b).split(b"z")[0]) is bytes)
check("bytes subclass no-match value", lambda: SubBytes(b).split(b"z")[0] == b)

# mutable receivers never reuse (CPython guards with STRINGLIB_MUTABLE).
check("bytearray no-match type", lambda: type(ba.split(b"z")[0]) is bytearray)
check("bytearray no-match value", lambda: ba.split(b"z")[0] == ba)
check("bytearray no-match is new", lambda: ba.split(b"z")[0] is not ba)
check("bytearray matched", lambda: ba.split(b"-") == [bytearray(b"abc"), bytearray(b"def")])

# whitespace mode drops the separator, so its single piece is not the receiver.
check("str whitespace no reuse", lambda: (lambda w: w.split()[0] is not w)(" abc"))
check("str whitespace value", lambda: " abc".split() == ["abc"])
check("str whitespace match", lambda: " a b ".split() == ["a", "b"])
check("bytes whitespace value", lambda: b" abc".split() == [b"abc"])
check("bytearray whitespace value", lambda: ba.split() == [ba])

# errors and edge shapes are untouched by the shortcut.
check("empty separator still errors", lambda: _raises(ValueError, lambda: s.split("")))
check("str sep wrong type errors", lambda: _raises(TypeError, lambda: s.split(b"z")))
check("maxsplit non-int errors", lambda: _raises(TypeError, lambda: s.split("-", "x")))
check("split of 1-char string", lambda: ("a".split("b")[0] == "a"))
check("sep equal to receiver", lambda: s.split(s) == ["", ""])
check("sep equal to receiver reuse", lambda: s.split(s + "z")[0] is s)


def _raises(exc, fn):
    try:
        fn()
    except exc:
        return True
    return False


def main():
    failed = []
    for name, fn in CHECKS:
        try:
            ok = fn()
        except Exception as e:  # noqa: BLE001 - the probe reports, it does not fix
            failed.append(f"{name}: raised {type(e).__name__}: {e}")
            continue
        if ok is not True:
            failed.append(f"{name}: got {ok!r}")
    print(f"{len(CHECKS) - len(failed)}/{len(CHECKS)} checks pass")
    for line in failed:
        print("  FAIL", line)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
