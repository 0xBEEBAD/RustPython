"""Which integer arguments of str/bytes methods actually consult `__index__`?

They are supposed to. CPython 3.15 runs every one of these through
`_PyNumber_Index` (`Objects/abstract.c`), while our argument binders
(`TryFromObject for isize` / `Option<PyIntRef>`) do an `isinstance` check and
raise, so `s.split(",", Idx(1))` fails here and works there - and nothing in the
test suite notices, because `Lib/test/string_tests.py` contains zero
occurrences of `__index__` and the hits in `test_bytes.py` are
mutation-during-index bounds tests, not argument acceptance. So this file, not
the suite, is the before/after harness for task #110.

    bench/labs/variants/rp-lite-119.exe bench/labs/ix_probe.py
    bench/labs/cp314/python.exe         bench/labs/ix_probe.py

Run it after the fix and diff the two outputs: the `Idx`/`BadFloat`/`RaiseIdx`
rows must turn into values, `__index__() must return an int` must appear, and
the RuntimeError from `RaiseIdx` must propagate instead of being swallowed.
"""
import sys

class Idx:
    def __init__(self, v=1):
        self.v = v
    def __index__(self):
        return self.v

class BadFloat:
    def __index__(self):
        return 1.5

class BadStr:
    def __index__(self):
        return "1"

class RaiseIdx:
    def __index__(self):
        raise RuntimeError("boom")

class MyInt(int):
    pass

def show(label, fn):
    try:
        print(label, "=>", repr(fn()))
    except BaseException as e:
        print(label, "=>", type(e).__name__, e)

print("PY", sys.version_info[:3])
show("split Idx(1)", lambda: "a,b,c".split(",", Idx(1)))
show("replace Idx(1)", lambda: "aaa".replace("a", "b", Idx(1)))
show("count Idx(0,Idx(2))", lambda: "abc".count("x", Idx(0), Idx(2)))
show("startswith Idx(1)", lambda: "abc".startswith("b", Idx(1)))
show("find Idx(1)", lambda: "abc".find("b", Idx(1)))
show("split None-maxsplit", lambda: "a,b".split(",", None))
show("startswith None-start", lambda: "abc".startswith("b", None))
show("split 2**63", lambda: "a,b".split(",", 2**63))
show("split 2**70", lambda: "a,b".split(",", 2**70))
show("startswith 2**70", lambda: "abc".startswith("z", 2**70))
show("startswith 2**70 empty", lambda: "abc".startswith("", 2**70))
show("find 2**70", lambda: "abc".find("c", 2**70))
show("count 2**70", lambda: "abc".count("c", 2**70))
show("startswith -2**70", lambda: "abc".startswith("a", -2**70))
show("split True", lambda: "a,b,c".split(",", True))
show("startswith True", lambda: "abc".startswith("b", True))
show("split MyInt(1)", lambda: "a,b,c".split(",", MyInt(1)))
show("startswith MyInt(1)", lambda: "abc".startswith("b", MyInt(1)))
show("startswith 1.0", lambda: "abc".startswith("b", 1.0))
show("startswith BadFloat", lambda: "abc".startswith("b", BadFloat()))
show("startswith BadStr", lambda: "abc".startswith("b", BadStr()))
show("startswith RaiseIdx", lambda: "abc".startswith("b", RaiseIdx()))
show("split RaiseIdx", lambda: "a,b".split(",", RaiseIdx()))
show("startswith str-noindex", lambda: "abc".startswith("b", "x"))
show("split str-noindex", lambda: "a,b".split(",", "x"))
show("startswith neg", lambda: "abc".startswith("c", -1))
show("zfill Idx", lambda: "1".zfill(Idx(4)))
show("center Idx", lambda: "a".center(Idx(3)))
show("expandtabs Idx", lambda: "\t".expandtabs(Idx(2)))
