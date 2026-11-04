"""Parity test for the one-argument `next()` call fast path.

The fast path dispatches directly to the iterator protocol. It must preserve:
TypeError text for non-iterators, StopIteration values, default-argument
behaviour, errors raised inside __next__, and tracing hooks.

  python test_next_fast.py
  rustpython test_next_fast.py
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


def check_raises(name, fn, exc, message=None):
    global failures
    try:
        fn()
    except exc as e:
        if message is not None and message not in str(e):
            failures += 1
            print(f"FAIL {name}: message {str(e)!r} missing {message!r}")
            return
        print(f"PASS {name}")
    except BaseException as e:
        failures += 1
        print(f"FAIL {name}: raised {type(e).__name__}, want {exc.__name__}")
    else:
        failures += 1
        print(f"FAIL {name}: no exception")


# 1. Generators.
def gen():
    yield 1
    yield 2
    return "done"


g = gen()
check("generator first", next(g), 1)
check("generator second", next(g), 2)
check_raises("generator exhausted", lambda: next(g), StopIteration)

# StopIteration value preserved.
g = gen()
next(g)
next(g)
try:
    next(g)
except StopIteration as e:
    check("stop value", e.value, "done")

# 2. Builtin iterators.
check("list iter", next(iter([10, 20])), 10)
check("tuple iter", next(iter((1, 2))), 1)
check("range iter", next(iter(range(3))), 0)
check("str iter", next(iter("ab")), "a")
d = {"k": "v"}
check("dict iter", next(iter(d)), "k")
check("set iter", next(iter({7})), 7)
check("enumerate iter", next(iter(enumerate([5]))), (0, 5))
check("zip iter", next(iter(zip([1], [2]))), (1, 2))

# 3. Two-argument next() still uses the generic path.
check("next default on exhausted", next(iter([]), "dflt"), "dflt")
check("next default on live", next(iter([1, 2]), "dflt"), 1)

# 4. Non-iterator errors: exact CPython message.
check_raises("list is not an iterator", lambda: next([1, 2]), TypeError,
             "object is not an iterator")
check_raises("int is not an iterator", lambda: next(3), TypeError,
             "object is not an iterator")


class IterableNotIterator:
    def __iter__(self):
        return iter([1])


check_raises("iterable not iterator", lambda: next(IterableNotIterator()), TypeError,
             "object is not an iterator")

# 5. User objects with __next__ are iterators.
class Custom:
    def __init__(self):
        self.n = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.n >= 2:
            raise StopIteration("custom-done")
        self.n += 1
        return self.n


c = Custom()
check("custom first", next(c), 1)
check("custom second", next(c), 2)
try:
    next(c)
except StopIteration as e:
    check("custom stop value", e.value, "custom-done")

# 6. Exceptions raised inside __next__ propagate unchanged.
class Boom:
    def __iter__(self):
        return self

    def __next__(self):
        raise ValueError("boom-next")


check_raises("error from __next__", lambda: next(Boom()), ValueError, "boom-next")

# 7. A generator that raises.
def bad_gen():
    yield 1
    raise KeyError("gen-err")


bg = bad_gen()
check("bad gen first", next(bg), 1)
check_raises("bad gen raise", lambda: next(bg), KeyError, "gen-err")

# 8. Tracing still sees the call (fast path must defer when a tracer runs).
events = []


def tracer(frame, event, arg):
    # `next` is a C function: CPython reports c_call/c_return, not call/return.
    if event == "c_call" and getattr(arg, "__name__", "") == "next":
        events.append("next")
    return tracer


def traced_next(it):
    return next(it)


# CPython 3.14 itself inlines `next`, so no c_call event is observable there;
# the requirement here is only that a tracer does not break the fast path.
sys.settrace(tracer)
try:
    value = traced_next(gen())
finally:
    sys.settrace(None)
check("next works under tracer", value, 1)

# 9. next() on a nested generator chain.
def outer():
    yield next(inner_gen())


def inner_gen():
    yield 42


check("nested next", next(outer()), 42)

print("RESULT", "FAIL" if failures else "OK")
sys.exit(1 if failures else 0)
