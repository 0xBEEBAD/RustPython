"""Parity test for generator close()/finalization fast paths.

A generator whose frame has no exception handling and is not delegating can be
closed by just releasing its locals: resuming it with GeneratorExit could only
unwind. These checks pin everything observable around close: finally blocks,
with-blocks, yield-from delegation, ignored GeneratorExit, locals release,
destruction, and double close.

  python test_gen_close_fast.py
  rustpython test_gen_close_fast.py
"""
import gc
import sys
import weakref

failures = 0


def check(name, got, want):
    global failures
    if got == want:
        print(f"PASS {name}")
    else:
        failures += 1
        print(f"FAIL {name}: got {got!r}, want {want!r}")


def check_raises(name, fn, exc, message=None):
    global failures
    try:
        fn()
    except exc as e:
        if message is not None and message not in str(e):
            failures += 1
            print(f"FAIL {name}: {str(e)!r} missing {message!r}")
            return
        print(f"PASS {name}")
    except BaseException as e:
        failures += 1
        print(f"FAIL {name}: raised {type(e).__name__}: {e}, want {exc.__name__}")
    else:
        failures += 1
        print(f"FAIL {name}: no exception")


# 1. Plain generator: close returns None, it becomes exhausted.
def plain():
    yield 1
    yield 2


g = plain()
next(g)
check("close returns None", g.close(), None)
check_raises("closed is exhausted", lambda: next(g), StopIteration)
check("close twice", g.close(), None)
check("gi_frame after close", g.gi_frame, None)

# 2. finally still runs on close.
ran = []


def with_finally():
    try:
        yield 1
        yield 2
    finally:
        ran.append("finally")


g = with_finally()
next(g)
g.close()
check("close runs finally", ran, ["finally"])

# 3. with-block __exit__ runs on close.
class Ctx:
    def __init__(self):
        self.exited = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.exited = True
        return False


ctx = Ctx()


def with_block():
    with ctx:
        yield 1
        yield 2


g = with_block()
next(g)
g.close()
check("close runs __exit__", ctx.exited, True)

# 4. yield-from: closing the outer generator closes the inner one.
inner_ran = []


def inner():
    try:
        yield 10
        yield 20
    finally:
        inner_ran.append("inner-finally")


def outer():
    yield from inner()


g = outer()
check("yield-from first", next(g), 10)
g.close()
check("close closes sub-generator", inner_ran, ["inner-finally"])

# 5. GeneratorExit that is swallowed and yields again is an error.
def ignoring():
    try:
        yield 1
    except GeneratorExit:
        yield 2


g = ignoring()
next(g)
check_raises("ignored GeneratorExit", g.close, RuntimeError, "ignored GeneratorExit")

# 6. Locals are released on close (weakref dies).
class Payload:
    pass


ref_holder = []


def holds_local():
    obj = Payload()
    ref_holder.append(weakref.ref(obj))
    yield 1
    yield 2


g = holds_local()
next(g)
g.close()
gc.collect()
check("locals released on close", ref_holder[0](), None)

# 7. Destruction of a suspended generator releases locals too.
ref_holder2 = []


def holds_local2():
    obj = Payload()
    ref_holder2.append(weakref.ref(obj))
    yield 1


g = holds_local2()
next(g)
del g
gc.collect()
check("locals released on del", ref_holder2[0](), None)

# 8. Closing a generator from inside itself is an error (re-entrancy).
g8 = None


def self_closer():
    try:
        g8.close()
    except ValueError as e:
        yield str(e)


g8 = self_closer()
check("close while running", next(g8).startswith("generator already executing"), True)

# 9. A closed generator's code with a return value.
def returns_value():
    yield 1
    return "done"


g = returns_value()
next(g)
try:
    next(g)
except StopIteration as e:
    check("return value via StopIteration", e.value, "done")

# 10. Async generators are unaffected by generator close paths.
import asyncio


async def agen():
    yield 1


async def consume():
    out = []
    async for v in agen():
        out.append(v)
    return out


check("async generator", asyncio.run(consume()), [1])

# 11. sys.monitoring observes the GeneratorExit unwind, so close must not skip it.
mon = sys.monitoring
TOOL = 3
mon.use_tool_id(TOOL, "close-test")
seen = []


def on_unwind(code, offset, exc):
    seen.append(("unwind", type(exc).__name__, code.co_name))


mon.register_callback(TOOL, mon.events.PY_UNWIND, on_unwind)
mon.set_events(TOOL, mon.events.PY_UNWIND)
try:
    g = plain()
    next(g)
    g.close()
finally:
    mon.set_events(TOOL, 0)
    mon.register_callback(TOOL, mon.events.PY_UNWIND, None)
    mon.free_tool_id(TOOL)
check("close unwind under monitoring", seen, [("unwind", "GeneratorExit", "plain")])

print("RESULT", "FAIL" if failures else "OK")
sys.exit(1 if failures else 0)
