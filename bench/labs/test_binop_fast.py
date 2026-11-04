"""Behavioral parity test for exact-type binary-op fast paths.

The interpreter takes a borrowed-ref fast path for exact int/float arithmetic
and the `"%s" % str` quirk. This test pins the observable semantics (results,
types, exceptions, and subclass deopt) so both interpreters agree.

  python test_binop_fast.py
  rustpython test_binop_fast.py
"""
import sys

failures = 0


def check(name, got, want):
    global failures
    if got == want and type(got) is type(want):
        print(f"PASS {name}")
    else:
        failures += 1
        print(f"FAIL {name}: got {got!r} ({type(got).__name__}), want {want!r}")


def check_raises(name, fn, exc):
    global failures
    try:
        fn()
    except exc:
        print(f"PASS {name}")
    except BaseException as e:
        failures += 1
        print(f"FAIL {name}: raised {type(e).__name__}, want {exc.__name__}")
    else:
        failures += 1
        print(f"FAIL {name}: no exception, want {exc.__name__}")


# int + int / - / * keep int type, including over the 256 small-int cache edge
check("int add", 200 + 100, 300)
check("int add big", 10**20 + 1, 10**20 + 1)
check("int sub", 5 - 8, -3)
check("int mul", 7 * 6, 42)
check("int mul big", 2**40 * 4, 2**42)
def inplace_add():
    x = 41
    x += 1
    return x


check("int inplace", inplace_add(), 42)

# float + float / - / *
check("float add", 1.5 + 2.5, 4.0)
check("float sub", 1.5 - 2.5, -1.0)
check("float mul", 1.5 * 2.0, 3.0)
check("float inf", 1e308 + 1e308, float("inf"))

# mixed int/float goes through the generic path and stays correct
check("int+float", 1 + 2.5, 3.5)
check("float+int", 2.5 + 1, 3.5)

# floor division / modulo, including negative operands (Python floor semantics)
check("floordiv", 7 // 2, 3)
check("floordiv neg", -7 // 2, -4)
check("floordiv big", 10**19 // 3, 10**19 // 3)
check("mod", 7 % 3, 1)
check("mod neg", -7 % 3, 2)
check("mod big", 10**19 % 3, 10**19 % 3)
check_raises("floordiv zero", lambda: 1 // 0, ZeroDivisionError)
check_raises("mod zero", lambda: 1 % 0, ZeroDivisionError)

# the "%s" % str quirk returns the argument string itself
s = "hello"
r = "%s" % s
check("percent-s value", r, "hello")
check("percent-s identity", r is s, True)

# bool is an int subclass but must keep bool results from `+`
check("bool add", True + True, 2)
check("bool type", type(True + True).__name__, "int")

# subclasses must deopt to the generic protocol and observe overrides
class WeirdInt(int):
    def __add__(self, other):
        return "weird-add"

    def __sub__(self, other):
        return "weird-sub"

    def __mul__(self, other):
        return "weird-mul"


check("int subclass add", WeirdInt(1) + 1, "weird-add")
check("int subclass sub", WeirdInt(1) - 1, "weird-sub")
check("int subclass mul", WeirdInt(1) * 2, "weird-mul")


class WeirdFloat(float):
    def __add__(self, other):
        return "weird-fadd"


check("float subclass add", WeirdFloat(1.0) + 1.0, "weird-fadd")

# reflected ops on the right operand must still run
class Reflected:
    def __radd__(self, other):
        return "reflected-add"

    def __rsub__(self, other):
        return "reflected-sub"


check("reflected add", 1 + Reflected(), "reflected-add")
check("reflected sub", 1 - Reflected(), "reflected-sub")

# string concatenation and repetition stay correct
check("str add", "a" + "b", "ab")
check("str mul", "ab" * 2, "abab")

print("RESULT", "FAIL" if failures else "OK")
sys.exit(1 if failures else 0)
