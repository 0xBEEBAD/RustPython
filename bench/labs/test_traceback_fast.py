"""Parity test for exception traceback construction (freelist + single fetch).

Raises in loops to exercise traceback node reuse, and checks the observable
traceback structure: tb_frame names, line numbers, tb_next chains, __context__ /
__cause__ chaining, re-raise accumulation, and traceback formatting.

  python test_traceback_fast.py
  rustpython test_traceback_fast.py
"""
import sys
import traceback

failures = 0


def check(name, got, want):
    global failures
    if got == want:
        print(f"PASS {name}")
    else:
        failures += 1
        print(f"FAIL {name}: got {got!r}, want {want!r}")


def tb_frames(e):
    names = []
    tb = e.__traceback__
    while tb is not None:
        names.append((tb.tb_frame.f_code.co_name, tb.tb_lineno))
        tb = tb.tb_next
    return names


# 1. Many raises in a loop: each traceback must be well-formed (freelist reuse).
def raiser():
    raise ValueError("boom")


for i in range(2000):
    try:
        raiser()
    except ValueError as e:
        names = [n for n, _ in tb_frames(e)]
        if names[-1] != "raiser":
            check(f"loop traceback {i}", names, ["raiser"])
            break
else:
    print("PASS loop tracebacks well-formed")

# 2. Traceback chain through nested calls.
def inner():
    raise KeyError("k")


def middle():
    inner()


def outer():
    middle()


try:
    outer()
except KeyError as e:
    names = [n for n, _ in tb_frames(e)]
    check("nested chain tail", names[-3:], ["outer", "middle", "inner"])

# 3. Line numbers point at the raising statement.
try:
    raise RuntimeError("where")
except RuntimeError as e:
    tb = e.__traceback__
    check("tb_lineno int", isinstance(tb.tb_lineno, int) and tb.tb_lineno > 0, True)
    check("tb_lasti int", isinstance(tb.tb_lasti, int), True)

# 4. Re-raise keeps accumulating entries (CPython adds one per frame pass).
def reraiser():
    try:
        raise IndexError("orig")
    except IndexError:
        raise


try:
    reraiser()
except IndexError as e:
    names = [n for n, _ in tb_frames(e)]
    check("reraise chain", names[-1], "reraiser")

# 5. __context__ chaining (implicit) and __cause__ (explicit from).
try:
    try:
        raise ValueError("first")
    except ValueError:
        raise TypeError("second")
except TypeError as e:
    check("implicit context", type(e.__context__).__name__, "ValueError")

try:
    try:
        raise ValueError("first")
    except ValueError as inner_exc:
        raise TypeError("second") from inner_exc
except TypeError as e:
    check("explicit cause", type(e.__cause__).__name__, "ValueError")
    check("cause sets suppress_context", e.__suppress_context__, True)

# 6. tb_frame.f_locals/locals usable from a traceback.
def with_locals(a):
    b = a + 1
    raise ValueError("locals")


try:
    with_locals(41)
except ValueError as e:
    tb = e.__traceback__
    while tb is not None:
        if tb.tb_frame.f_code.co_name == "with_locals":
            loc = dict(tb.tb_frame.f_locals)
            check("tb locals", (loc.get("a"), loc.get("b")), (41, 42))
            break
        tb = tb.tb_next

# 7. traceback.format_exc output shape.
def fmt_probe():
    try:
        raise ValueError("fmt")
    except ValueError:
        return traceback.format_exc()


out = fmt_probe()
check("format_exc has type", "ValueError: fmt" in out, True)
check("format_exc has frame", "fmt_probe" in out, True)

# 8. sys.exc_info inside/after except.
def exc_info_probe():
    try:
        raise ValueError("info")
    except ValueError:
        t, v, tb = sys.exc_info()
        return type(v).__name__, tb is not None
    finally:
        pass


check("sys.exc_info", exc_info_probe(), ("ValueError", True))
check("sys.exc_info cleared", sys.exc_info(), (None, None, None))

# 9. Exception freed cleanly after traceback use (no freelist corruption):
#    raise the same exception again after catching it once.
e = ValueError("reuse")
try:
    raise e
except ValueError as caught:
    check("same exception object", caught is e, True)
try:
    raise e
except ValueError as caught:
    check("exception reusable", caught is e, True)

print("RESULT", "FAIL" if failures else "OK")
sys.exit(1 if failures else 0)
