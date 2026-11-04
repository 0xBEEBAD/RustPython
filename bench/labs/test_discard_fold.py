"""Parity test for discarding unused call / binary-op results (POP_TOP folding).

When the instruction after a call or BINARY_OP is POP_TOP, the result is
unused; the interpreter may drop it without pushing. These checks pin the
observable behavior: side effects, exceptions, values that are stored, method
descriptors, generators and tracing/monitoring observation.

  python test_discard_fold.py
  rustpython test_discard_fold.py
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


calls = []


def effect(x):
    calls.append(x)
    return x * 2


def discard_loop(n):
    for i in range(n):
        effect(i)


discard_loop(5)
check("discarded call side effects", calls, [0, 1, 2, 3, 4])


def raising():
    raise ValueError("boom")


def discard_raising():
    for _ in range(1):
        raising()


check_raises("discarded raising call", discard_raising, ValueError)


def stored():
    return 21


x = stored()
check("stored result", x, 21)


def stored_loop(n):
    total = 0
    for i in range(n):
        total = effect(i)
    return total


check("stored in loop", stored_loop(4), 6)


class C:
    def m(self, a):
        calls.append(("m", a))
        return a + 1


obj = C()


def discard_method(n):
    for i in range(n):
        obj.m(i)


calls.clear()
discard_method(3)
check("discarded method calls", calls, [("m", 0), ("m", 1), ("m", 2)])


def discard_descriptor(n):
    s = "abcdef"
    for _ in range(n):
        s.upper()
        s.split("d")
        len(s)
        (3).bit_length()


discard_descriptor(2)


def discard_format(n):
    for _ in range(n):
        "%s=%d" % ("x", 42)


discard_format(2)


def gen():
    yield 1
    yield 2


def discard_next(n):
    for _ in range(n):
        g = gen()
        next(g)
        next(g)


discard_next(2)


def discard_binop(n):
    a = 5
    b = 7
    for _ in range(n):
        a + b
        a * b
        a < b


discard_binop(2)

# Tracing still observes the discarded statements.
events = []


def tracer(frame, event, arg):
    if event == "line" and frame.f_code.co_name == "traced":
        events.append(frame.f_lineno)
    return tracer


def traced(n):
    for _ in range(n):
        effect(1)


sys.settrace(tracer)
try:
    traced(3)
finally:
    sys.settrace(None)
check("tracing observed lines", len(events) > 0, True)

# Monitoring instruction events still fire for discarded calls.
mon = sys.monitoring
TOOL = 5
mon.use_tool_id(TOOL, "discard-test")
seen = []


def on_instruction(code, offset):
    if code.co_name == "monitored":
        seen.append(offset)


mon.register_callback(TOOL, mon.events.INSTRUCTION, on_instruction)
mon.set_events(TOOL, mon.events.INSTRUCTION)


def monitored():
    for _ in range(2):
        effect(2)


try:
    monitored()
finally:
    mon.set_events(TOOL, 0)
    mon.register_callback(TOOL, mon.events.INSTRUCTION, None)
    mon.free_tool_id(TOOL)
check("monitoring fired", len(seen) > 0, True)

print("RESULT", "FAIL" if failures else "OK")
sys.exit(1 if failures else 0)
