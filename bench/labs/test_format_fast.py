"""Parity test for the str `%` fast path (bare %s/%d with an exact tuple).

  python test_format_fast.py
  rustpython test_format_fast.py
"""
import sys

failures = 0


def check(name, got, want):
    global failures
    if got == want:
        print(f"PASS {name}")
    else:
        failures += 1
        print(f"FAIL {name}: got {got!r}, want {want!r}")


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


class S(str):
    def __str__(self):
        return "S!"


class I(int):
    pass


# fast-path shapes
check("basic", "%s=%d" % ("x", 42), "x=42")
check("all d", "%d-%d-%d" % (1, -2, 0), "1--2-0")
check("all s", "%s%s" % ("a", "b"), "ab")
check("percent literal", "100%% of %d" % (5,), "100% of 5")
check("no space", "%d" % (7,), "7")
check("leading literal", "n=%d" % (10,), "n=10")
check("trailing percent", "%d%%" % (10,), "10%")
check("i64 min", "%d" % (-9223372036854775808,), "-9223372036854775808")
check("i64 max", "%d" % (9223372036854775807,), "9223372036854775807")
check("unicode template", "héllo %d ✓" % (5,), "héllo 5 ✓")
check("unicode arg", "%s!" % ("héllo",), "héllo!")

# fallbacks that must keep CPython semantics
check("width", "%5d" % (42,), "   42")
check("left align", "%-5s|" % ("ab",), "ab   |")
check("zero pad", "%05d" % (42,), "00042")
check("precision", "%.2s" % ("abcdef",), "ab")
check("plus flag", "%+d" % (42,), "+42")
check("hex", "%x" % (255,), "ff")
check("repr", "%r" % ("x",), "'x'")
check("float conv", "%f" % (1.5,), "1.500000")
check("float with d", "%d" % (3.9,), "3")
check("bool with d", "%d" % (True,), "1")
check("int subclass", "%d" % (I(5),), "5")
check("str subclass", "%s" % (S("x"),), "S!")
check("none with s", "%s" % (None,), "None")
check("one non-tuple arg", "%s" % "x", "x")
check("empty template", "" % (), "")
check("empty tuple no specs", "abc" % (), "abc")
check("big int", "%d" % (10**30,), "1" + "0" * 30)
check("mapping", "%(a)s" % {"a": 1}, "1")
check("percent only", "%%" % (), "%")

# arity errors still come from the generic formatter
check_raises("too few args", lambda: "%s %s" % ("a",), TypeError)
check_raises("too many args", lambda: "%s" % ("a", "b"), TypeError)
check_raises("bad type for d", lambda: "%d" % ("x",), TypeError)

print("RESULT", "FAIL" if failures else "OK")
sys.exit(1 if failures else 0)
