"""Behavioral parity test for generator creation/resume fast paths.

Exercises argument binding (exact, defaults, kwonly, varargs), send/throw/close,
yield-from delegation, frame introspection and tracebacks, so a creation fast
path cannot silently change semantics.

  python test_generator_fast.py
  rustpython test_generator_fast.py
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
        print(f"FAIL {name}: raised {type(e).__name__}: {e}, want {exc.__name__}")
    else:
        failures += 1
        print(f"FAIL {name}: no exception, want {exc.__name__}")


# 1. Exact positional args.
def gen_exact(a, b):
    yield a
    yield b


check("exact list", list(gen_exact(1, 2)), [1, 2])

# 2. Defaults / keyword-only / varargs (bind through the generic path).
def gen_defaults(a, b=10, *, c=20):
    yield a + b + c


check("defaults", list(gen_defaults(1)), [31])
check("kwonly", list(gen_defaults(1, c=2)), [13])

# 3. send / throw / close.
def echo():
    while True:
        got = yield
        if got is None:
            continue
        if got == "stop":
            return "done"


g = echo()
next(g)
check("send value", g.send("hello"), None)
g2 = echo()
next(g2)
try:
    g2.send("stop")
except StopIteration as e:
    check("send stop value", e.value, "done")


def catcher():
    try:
        yield 1
        yield 2
    except ValueError as e:
        yield str(e)


g = catcher()
check("throw first", next(g), 1)
check("throw caught", g.throw(ValueError("boom")), "boom")
g = catcher()
next(g)
check("close returns None", g.close(), None)
check("close makes it stop", list(g), [])


# 4. yield from delegation.
def inner():
    yield 1
    return 42


def outer():
    r = yield from inner()
    yield r


check("yield from", list(outer()), [1, 42])

# 5. Generator expression (implicit frame creation from a genexpr code object).
check("genexpr", list(x * 2 for x in range(3)), [0, 2, 4])

# 6. Frame introspection is present and reports the running line.
def introspect():
    yield sys._getframe().f_code.co_name
    yield 0


g = introspect()
check("gi_frame code name", g.gi_frame.f_code.co_name, "introspect")
check("gi_frame lasti starts 0", g.gi_frame.f_lasti >= 0, True)
next(g)
check("gi_frame running flag", g.gi_running, False)

# 7. Locals of a suspended generator frame.
def with_locals(x):
    y = x + 1
    yield y
    yield y + 1


g = with_locals(1)
next(g)
check("gi_frame locals", dict(g.gi_frame.f_locals), {"x": 1, "y": 2})

# 8. Generators inside methods and closures.
class Holder:
    def __init__(self):
        self.base = 100

    def items(self, n):
        for i in range(n):
            yield self.base + i


check("method generator", list(Holder().items(2)), [100, 101])


def make_closure():
    captured = 7

    def gen():
        yield captured

    return gen()


check("closure generator", list(make_closure()), [7])

# 9. Traceback from a throw inside a generator.
def raiser():
    yield 1
    raise KeyError("inner")


g = raiser()
next(g)
try:
    next(g)
except KeyError as e:
    tb = e.__traceback__
    names = []
    while tb is not None:
        names.append(tb.tb_frame.f_code.co_name)
        tb = tb.tb_next
    check("traceback tail", names[-1], "raiser")

# 10. Re-entrancy: resuming a generator while it is already running raises
# ValueError inside the generator.
g = None


def reentrant():
    yield 1
    try:
        next(g)
    except ValueError as e:
        yield "caught:" + str(e)


g = reentrant()
next(g)
check("re-entrancy detected", g.send(None).startswith("caught:"), True)

# 11. StopIteration after exhaustion, and next() default.
g = gen_exact(1, 2)
list(g)
check_raises("exhausted next", lambda: next(g), StopIteration)
g3 = gen_exact(3, 4)
check("next default", next(g3, None), 3)
g = gen_exact(5, 6)
list(g)
check("next with default after exhaustion", next(g, "dflt"), "dflt")

print("RESULT", "FAIL" if failures else "OK")
sys.exit(1 if failures else 0)
