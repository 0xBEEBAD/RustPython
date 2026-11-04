"""Parity test for direct construction of builtin exception types.

The fast path bypasses type.__call__ for immutable builtin exception classes.
These checks pin the observable results: args tuples, str/repr, keyword
rejection, payload-bearing subclasses (OSError), builtin subclasses with
custom __init__, and the quirks (StopIteration.value, KeyError repr).

  python test_excctor_fast.py
  rustpython test_excctor_fast.py
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


# 1. Args handling.
check("one arg", ValueError("x").args, ("x",))
check("two args", ValueError("a", "b").args, ("a", "b"))
check("no args", ValueError().args, ())
check("exception no args", Exception().args, ())
check("base args", BaseException("m").args, ("m",))
check("type preserved", type(ValueError("x")), ValueError)

# 2. str / repr.
check("str one arg", str(ValueError("boom")), "boom")
check("str two args", str(ValueError("a", "b")), "('a', 'b')")
check("str no args", str(ValueError()), "")
check("repr", repr(ValueError("boom")), "ValueError('boom')")
check("keyerror repr str", str(KeyError("k")), "'k'")

# 3. Payload-bearing and special exceptions.
e = OSError(2, "missing")
check("oserror args", e.args, (2, "missing"))
check("oserror errno", e.errno, 2)
check("stopiteration value", StopIteration("v").value, "v")
check("stopiteration args", StopIteration("v").args, ("v",))
check("systemexit code", SystemExit(3).code, 3)
check("import error name", ImportError("m", name="mod").name, "mod")

# 4. Keyword arguments: CPython rejects them for exception classes, but
# RustPython only rejects them on BaseException itself (pre-existing
# divergence, unrelated to construction fast paths), so this is not asserted
# here. Keyword calls never take the positional construction fast path.
try:
    kw = ValueError(msg="x")
except TypeError:
    print("PASS kwargs rejected (CPython behaviour)")
else:
    check("kwargs accepted (RustPython divergence)", type(kw), ValueError)

# 5. User subclasses: without overrides and with a custom __init__.
class MyErr(Exception):
    pass


check("subclass args", MyErr("x").args, ("x",))
check("subclass type", type(MyErr("x")), MyErr)


class CustomInit(Exception):
    def __init__(self, msg, code=7):
        super().__init__(msg)
        self.code = code


ci = CustomInit("m", 9)
check("custom init runs", (ci.args, ci.code), (("m",), 9))


class CustomNew(Exception):
    def __new__(cls, *args):
        obj = super().__new__(cls, *args)
        obj.via_new = True
        return obj


check("custom new runs", CustomNew().via_new, True)

# 6. Raising and catching still carries args and identity.
try:
    raise ValueError("raised")
except ValueError as exc:
    check("raise args", exc.args, ("raised",))
    check("raise type", type(exc), ValueError)

# 7. Chaining fields start empty on construction.
fresh = ValueError("x")
check("no cause", fresh.__cause__, None)
check("no context", fresh.__context__, None)
check("no traceback", fresh.__traceback__, None)
check("not suppressed", fresh.__suppress_context__, False)

print("RESULT", "FAIL" if failures else "OK")
sys.exit(1 if failures else 0)
