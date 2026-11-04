"""Print CPython's answer for every `split` no-match shape, so the reuse rule
(the receiver object itself as the single element) can be pinned from
measurement rather than guessed, then asserted by test_split_reuse.py.

    bench/labs/cp314/python.exe bench/labs/splitreusevalues.py
"""


class S(str):
    pass


class B(bytes):
    pass


def rows():
    s = "abc-def"
    yield ("str no-match", s.split("z")[0] is s)
    yield ("str match piece", s.split("-")[0] is s)
    yield ("str 2 parts len", len(s.split("-")))
    yield ("subclass no-match identity", S(s).split("z")[0] is s)
    yield ("subclass no-match type", type(S(s).split("z")[0]).__name__)
    yield ("rsplit no-match", s.rsplit("z")[0] is s)
    yield ("rsplit match piece", s.rsplit("-")[-1] is s)
    yield ("maxsplit 0", s.split("-", 0)[0] is s)
    yield ("maxsplit 0 len", len(s.split("-", 0)))
    yield ("maxsplit 5 no-match", s.split("z", 5)[0] is s)
    yield ("negative maxsplit", s.split("z", -1)[0] is s)
    yield ("negative maxsplit 2 parts", s.split("-", -1) == ["abc", "def"])
    yield ("empty receiver", (lambda e: e.split("z")[0] is e)(""))
    yield ("sep longer than receiver", s.split("zzzzzzzz")[0] is s)
    yield ("keyword sep form", s.split(sep="z")[0] is s)
    yield ("whitespace mode not reused", (lambda w: w.split()[0] is w)(" abc"))
    yield ("whitespace mode value", (lambda w: w.split())(" abc"))
    u = "héllo-wörld"
    yield ("2-byte kind no-match", u.split("z")[0] is u)
    yield ("non-ascii sep no-match", s.split("é")[0] is s)
    yield ("surrogate-ish sep no-match", s.split("\ud7ff")[0] is s)
    b = bytes(bytearray(b"abc-def"))
    yield ("bytes no-match", b.split(b"z")[0] is b)
    yield ("bytes multi-char sep no-match", b.split(b"zz")[0] is b)
    yield ("bytes match piece", b.split(b"-")[0] is b)
    yield ("bytes subclass no-match type", type(B(b).split(b"z")[0]).__name__)
    ba = bytearray(b"abc-def")
    yield ("bytearray no-match type", type(ba.split(b"z")[0]).__name__)
    yield ("bytearray no-match identity", ba.split(b"z")[0] is ba)
    yield ("bytearray no-match value", bytes(ba.split(b"z")[0]))
    yield ("bytes maxsplit 0", b.split(b"-", 0)[0] is b)
    frozen = ("abc",)
    yield ("join of split", "-".join(s.split("z")) == "abc-def")
    yield ("element hash equal", hash(s.split("z")[0]) == hash(s))
    del frozen


for name, value in rows():
    print(f"{name:32s} {value!r}")
