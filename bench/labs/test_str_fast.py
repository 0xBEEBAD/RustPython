"""Parity test for partial string/len/format fast paths.

Covers: str concatenation across the SSO boundary and with non-ASCII input,
len() on exact builtin containers plus __len__-overriding subclasses, and
%-formatting with tuples, strings, scalars and mappings.

  python test_str_fast.py
  rustpython test_str_fast.py
"""
import sys

failures = 0


def check(name, got, want):
    global failures
    if got == want and type(got) is type(want):
        print(f"PASS {name}")
    else:
        failures += 1
        print(f"FAIL {name}: got {got!r}, want {want!r}")


# --- str concatenation ------------------------------------------------------
check("concat empty", "" + "", "")
check("concat ascii short", "abc" + "def", "abcdef")
check("concat sso boundary 22", "a" * 11 + "b" * 11, "a" * 11 + "b" * 11)
check("concat sso overflow 23", "a" * 11 + "b" * 12, "a" * 11 + "b" * 12)
check("concat long", "x" * 100 + "y" * 100, "x" * 100 + "y" * 100)
check("concat unicode", "héllo" + "wörld", "héllowörld")
check("concat unicode long", "é" * 12 + "ü" * 12, "é" * 12 + "ü" * 12)
check("concat emoji", "🐍" + "🦀", "🐍🦀")
check("concat mixed kind", "abc" + "é", "abcé")

s = "hello"
r = s + " world"
check("concat value", r, "hello world")
check("concat type", type(r).__name__, "str")

# in-place add keeps working
buf = "a"
buf += "b"
check("iadd", buf, "ab")

# --- len() on exact containers and subclasses -------------------------------
check("len list", len([1, 2, 3]), 3)
check("len tuple", len((1, 2)), 2)
check("len dict", len({"a": 1, "b": 2}), 2)
check("len str ascii", len("hello"), 5)
check("len str unicode", len("héllo"), 5)
check("len str emoji", len("🐍🦀"), 2)
check("len empty", len([]), 0)


class WeirdLenList(list):
    def __len__(self):
        return 42


class WeirdLenStr(str):
    def __len__(self):
        return 7


check("len list subclass override", len(WeirdLenList([1, 2, 3])), 42)
check("len str subclass override", len(WeirdLenStr("abc")), 7)

# --- %-formatting -----------------------------------------------------------
check("percent str", "%s" % "x", "x")
check("percent int", "%d" % 5, "5")
check("percent tuple", "%s-%d" % ("a", 3), "a-3")
check("percent mapping", "%(k)s" % {"k": "v"}, "v")
check("percent literal only", "plain" % (), "plain")
check("percent list arg", "%s" % [1, 2], "[1, 2]")
check("percent float", "%.2f" % 1.234, "1.23")
check("percent unicode", "%s" % "héllo", "héllo")

class WeirdGetitem:
    def __getitem__(self, key):
        return f"item:{key}"

check("percent custom mapping", "%(a)s" % WeirdGetitem(), "item:a")

# --- exact-str method kernel fast paths -------------------------------------
def check_raises(name, fn, exc):
    global failures
    try:
        fn()
    except exc:
        print(f"PASS {name}")
    except BaseException as e:
        failures += 1
        print(f"FAIL {name}: raised {type(e).__name__}: {e}, want {exc.__name__}")
    else:
        failures += 1
        print(f"FAIL {name}: no exception")


# Compare the bound (fast path) call against the unbound generic call.
for text in ("abc", "ABC", "aBc-123", "", "héllo", "héLLo", "x" * 100):
    check(f"upper {text[:8]!r}", text.upper(), str.upper(text))
    check(f"lower {text[:8]!r}", text.lower(), str.lower(text))
check("upper unicode", "héllo".upper(), "HÉLLO")
check("lower unicode", "HÉLLO".lower(), "héllo")
check("upper 100 chars", ("ab" * 50).upper(), "AB" * 50)
check("upper empty", "".upper(), "")

check("find present", "abcdef".find("cd"), 2)
check("find absent", "abcdef".find("zz"), -1)
check("find empty", "abc".find(""), 0)
check("find unicode", "héllo".find("llo"), 2)
check("find start arg", "abcabc".find("bc", 2), 4)
check("find start/end", "abcabc".find("bc", 2, 4), -1)
check("find 100 chars", ("ab" * 50).find("ba"), 1)


class UpperSub(str):
    def upper(self):
        return "SUB:" + super().upper()


class FindSub(str):
    def find(self, *args):
        return 99


check("subclass upper override", UpperSub("abc").upper(), "SUB:ABC")
check("subclass find override", FindSub("abc").find("a"), 99)
check("unbound str.upper", str.upper("aBc"), "ABC")
check("unbound str.find", str.find("abcdef", "cd"), 2)
check_raises("find int arg", lambda: "abc".find(1), TypeError)
check_raises("find bytes arg", lambda: "abc".find(b"a"), TypeError)

# tracing must not change results
import sys as _sys
_events = []


def _tracer(frame, event, arg):
    _events.append(event)
    return _tracer


_sys.settrace(_tracer)
try:
    _v1 = "aBc".upper()
    _v2 = "abcdef".find("cd")
finally:
    _sys.settrace(None)
check("upper under tracer", _v1, "ABC")
check("find under tracer", _v2, 2)

# --- join fast paths --------------------------------------------------------
check("join empty items", "-".join([]), "")
check("join single", "-".join(["abc"]), "abc")
_single = "abc"
check("join single identity", "-".join([_single]) is _single, True)
check("join 3", "-".join(["a", "b", "c"]), "a-b-c")
check("join empty sep", "".join(["ab", "cd"]), "abcd")
check("join sso edge", "-".join(["a" * 11, "b" * 10]), "a" * 11 + "-" + "b" * 10)
check("join sso overflow", "-".join(["a" * 11, "b" * 11]), "a" * 11 + "-" + "b" * 11)
check("join unicode", "·".join(["é", "ü"]), "é·ü")
check("join long", "-".join(["x" * 100, "y" * 100]), "x" * 100 + "-" + "y" * 100)
check("join empty strings", "-".join(["", ""]), "-")


class JoinSub(str):
    pass


check("join subclass element", "-".join([JoinSub("a"), "b"]), "a-b")
check("bytes join", b"-".join([b"a", b"b"]), b"a-b")

# string creation through new_str: lengths around the inline/SSO boundary
for n in (0, 1, 21, 22, 23, 24, 100):
    v = "z" * n
    check(f"new_str len {n}", repr(v), repr("z" * n))
check("utf8 creation", "héllo".encode("utf-8").decode("utf-8"), "héllo")

# --- split fast paths -------------------------------------------------------
check("split basic", "a,b,c".split(","), ["a", "b", "c"])
check("split empties", "a,,b".split(","), ["a", "", "b"])
check("split empty input", "".split(","), [""])
check("split only sep", ",".split(","), ["", ""])
check("split trailing", "a,".split(","), ["a", ""])
check("split maxsplit 1", "a,b,c".split(",", 1), ["a", "b,c"])
check("split maxsplit 0", "a,b,c".split(",", 0), ["a,b,c"])
check("split maxsplit negative", "a,b,c".split(",", -1), ["a", "b", "c"])
check("split whitespace", "a b  c".split(), ["a", "b", "c"])
check("split whitespace maxsplit", "a b  c".split(None, 1), ["a", "b  c"])
check("split unicode sep", "éXü".split("X"), ["é", "ü"])
check("split multi sep", "aaa".split("aa"), ["", "a"])
check("split long", ("ab," * 50).split(","), ["ab"] * 50 + [""])
check("split types", [type(p).__name__ for p in "a,b".split(",")], ["str", "str"])
check("split non-ascii data", "héllo".split("l"), ["hé", "", "o"])
check_raises("split empty sep", lambda: "abc".split(""), ValueError)
check("rsplit basic", "a,b,c".rsplit(",", 1), ["a,b", "c"])
check("partition", "a-b-c".partition("-"), ("a", "-", "b-c"))

# --- str.format auto-field fast paths ---------------------------------------
check("format basic", "{}:{}".format(1, 2), "1:2")
check("format str args", "{} {}".format("ab", "cd"), "ab cd")
check("format mixed", "x{}y{}z".format(1, "b"), "x1ybz")
check("format no fields", "plain".format(), "plain")
check("format empty", "".format(), "")
check("format negative", "{}".format(-42), "-42")
check("format big int", "{}".format(10**20), str(10**20))
check("format bool", "{}".format(True), "True")
check("format float", "{}".format(1.5), "1.5")
check("format none", "{}".format(None), "None")
check("format braces literal", "{{}}".format(), "{}")
check("format unicode", "{}é".format("ü"), "üé")
check("format long", "{}".format("x" * 100), "x" * 100)
check("format keyword", "{a}".format(a=5), "5")
check("format positional", "{0}{1}".format("a", "b"), "ab")


class FormatSub(str):
    def __format__(self, spec):
        return "SUB"


check("format subclass deopt", "{}".format(FormatSub("x")), "SUB")
check_raises("format missing arg", lambda: "{}".format(), IndexError)
check("format extra arg ignored", "{}".format(1, 2), "1")

# --- slicing fast paths -----------------------------------------------------
check("slice basic", "abcdef"[2:4], "cd")
check("slice to end", "abcdef"[3:], "def")
check("slice from start", "abcdef"[:2], "ab")
check("slice negative", "abcdef"[-2:], "ef")
check("slice negative both", "abcdef"[-4:-1], "cde")
check("slice full", "abcdef"[:], "abcdef")
_full = "abcdef"
check("slice full identity", _full[:] is _full, True)
check("slice empty range", "abcdef"[4:2], "")
check("slice out of range", "abcdef"[100:], "")
check("slice negative out", "abcdef"[-100:2], "ab")
check("slice empty string", ""[:], "")
check("slice unicode", "héllo"[1:3], "él")
check("slice unicode negative", "héllo"[:-1], "héll")
check("slice bool bound", "abcdef"[True:3], "bc")
check("slice huge bound", "abcdef"[10**20:], "")
_v = "abcdef"
check("slice step still works", _v[::2], "ace")
check("slice neg step", _v[::-1], "fedcba")
check("bytes slice", b"abcdef"[1:3], b"bc")
check("list slice", [1, 2, 3, 4][1:3], [2, 3])


class SliceSub(str):
    def __getitem__(self, item):
        return "SUB"


check("slice subclass deopt", SliceSub("abcdef")[1:3], "SUB")

# --- startswith fast path ----------------------------------------------------
check("startswith match", "abcdef".startswith("abc"), True)
check("startswith mismatch", "abcdef".startswith("abd"), False)
check("startswith empty affix", "abcdef".startswith(""), True)
check("startswith longer affix", "ab".startswith("abc"), False)
check("startswith whole", "abc".startswith("abc"), True)
check("startswith unicode", "héllo".startswith("hé"), True)
check("startswith unicode miss", "héllo".startswith("he"), False)
check("startswith tuple match", "abcdef".startswith(("x", "ab")), True)
check("startswith tuple miss", "abcdef".startswith(("x", "y")), False)
check("startswith bounds", "abcdef".startswith("cd", 2), True)
check("startswith bounds false", "abcdef".startswith("ab", 2), False)
check_raises("startswith int arg", lambda: "abc".startswith(1), TypeError)
check("endswith still works", "abcdef".endswith("def"), True)
check("bytes startswith", b"abcdef".startswith(b"abc"), True)


class StartsSub(str):
    def startswith(self, *args):
        return "SUB"


check("startswith subclass deopt", StartsSub("abc").startswith("a"), "SUB")

check("endswith match", "abcdef".endswith("def"), True)
check("endswith mismatch", "abcdef".endswith("abc"), False)
check("endswith empty", "abcdef".endswith(""), True)
check("endswith unicode", "héllo".endswith("llo"), True)
check("endswith tuple", "abcdef".endswith(("x", "ef")), True)
check("endswith bounds", "abcdef".endswith("cd", 0, 4), True)
check("rfind present", "abcabc".rfind("bc"), 4)
check("rfind absent", "abcabc".rfind("zz"), -1)
check("rfind unicode", "héllo".rfind("l"), 3)
check_raises("endswith int arg", lambda: "abc".endswith(1), TypeError)


class EndsSub(str):
    def endswith(self, *args):
        return "SUB"


check("endswith subclass deopt", EndsSub("abc").endswith("c"), "SUB")

# --- len() fast paths --------------------------------------------------------
check("len tuple", len((1, 2, 3)), 3)
check("len dict", len({"a": 1}), 1)
check("len unicode str", len("héllo"), 5)
check("len empty str", len(""), 0)
check("len long str", len("x" * 1000), 1000)
check("len set", len({1, 2}), 2)
check("len bytes", len(b"abcd"), 4)


class LenTuple(tuple):
    def __len__(self):
        return 99


check("len tuple subclass", len(LenTuple((1, 2))), 99)

print("RESULT", "FAIL" if failures else "OK")
sys.exit(1 if failures else 0)
