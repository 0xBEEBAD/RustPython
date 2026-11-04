"""Behavior of a call whose callee frame might never be built.

The micro-inline kernel answers `f(1, 2)` by adding two ints from the caller's
argument slots and pushing the result, without entering the callee's frame. That
is only sound for bodies that cannot raise and cannot observe frame state, so
every case that could be confused with it is pinned here - the accepted shapes,
the shapes that must fall back, and what each one must produce. Both routes (the
kernel and `LUNA_ABLATE=microinline`) must print the same thing.

    python bench/labs/test_microinline.py
"""

import sys


def show(label, fn):
    try:
        value = fn()
    except BaseException as exc:
        tb = exc.__traceback__
        names = []
        while tb is not None:
            names.append(tb.tb_frame.f_code.co_name)
            tb = tb.tb_next
        print(f"{label:34s} {type(exc).__name__}: {exc} | tb={names}")
    else:
        print(f"{label:34s} {value!r}")


def add(a, b):
    return a + b


def sub(a, b):
    return a - b


def mul(a, b):
    return a * b


def div(a, b):
    return a / b


def concat(a, b):
    return a + b


def add_const(a):
    return a + 1


def two_ops(a, b):
    return a + b + 1


def with_docstring(a, b):
    """Adds."""
    return a + b


def with_global(a, b):
    return a + TOTAL


def with_call(a, b):
    return add(a, b)


def with_default(a, b=2):
    return a + b


def with_starargs(a, b, *rest):
    return a + b


def with_kwargs(a, b, **kw):
    return a + b


def with_try(a, b):
    try:
        return a + b
    finally:
        pass


def with_nested_func(a, b):
    def inner():
        return a
    return inner() + b


def raises_body(a, b):
    return a + b + undefined_name  # noqa: F821


def no_return(a, b):
    a + b


def bare_return(a, b):
    return


class Box:
    def __init__(self, v):
        self.v = v

    def m(self, a):
        return self.v + a

    def __add__(self, other):
        return f"boxed+{other!r}"


class IntLike(int):
    pass


def gen(a, b):
    yield a + b


TOTAL = 100
box = Box(5)

show("add(1, 2)", lambda: add(1, 2))
show("add(True, 1)", lambda: add(True, 1))
show("add(2**70, 1)", lambda: add(2**70, 1))
show("add(-1, -2)", lambda: add(-1, -2))
show("sub(5, 3)", lambda: sub(5, 3))
show("mul(6, 7)", lambda: mul(6, 7))
show("div(6, 3)", lambda: div(6, 3))
show("div(6, 0)", lambda: div(6, 0))
show("add(1.5, 2.5)", lambda: add(1.5, 2.5))
show("add('a', 'b')", lambda: concat("a", "b"))
show("add(Box, 1)", lambda: concat(box, 1))
show("add(1, Box)", lambda: concat(1, box))
show("add(IntLike(1), 2)", lambda: add(IntLike(1), 2))
show("add(None, 1)", lambda: add(None, 1))
show("add('s', 1)", lambda: add("s", 1))
show("add(1, 2, 3)", lambda: add(1, 2, 3))
show("add(**{'a': 1, 'b': 2})", lambda: add(**{"a": 1, "b": 2}))
show("add(a=1, b=2)", lambda: add(a=1, b=2))
show("add_const(41)", lambda: add_const(41))
show("two_ops(1, 2)", lambda: two_ops(1, 2))
show("with_docstring(1, 2)", lambda: with_docstring(1, 2))
show("with_global(1, 2)", lambda: with_global(1, 2))
show("with_call(1, 2)", lambda: with_call(1, 2))
show("with_default(1)", lambda: with_default(1))
show("with_default(1, 5)", lambda: with_default(1, 5))
show("with_starargs(1, 2)", lambda: with_starargs(1, 2))
show("with_starargs(1, 2, 3)", lambda: with_starargs(1, 2, 3))
show("with_kwargs(1, 2)", lambda: with_kwargs(1, 2))
show("with_kwargs(1, 2, z=3)", lambda: with_kwargs(1, 2, z=3))
show("with_try(1, 2)", lambda: with_try(1, 2))
show("with_nested_func(1, 2)", lambda: with_nested_func(1, 2))
show("raises_body(1, 2)", lambda: raises_body(1, 2))
show("no_return(1, 2)", lambda: no_return(1, 2))
show("bare_return(1, 2)", lambda: bare_return(1, 2))
show("box.m(5)", lambda: box.m(5))
show("gen(1, 2) next", lambda: next(gen(1, 2)))
show("add.__name__", lambda: add.__name__)
show("add(1, 2) twice identity", lambda: add(1, 2) is add(1, 2))
show("sum of 2000 inline adds", lambda: sum(add(i, 1) for i in range(2000)))

# Tracing must still see every call, so the kernel has to stand down while a
# tracer is installed. Count events with and without the tracer on the same call.
events = []


def tracer(frame, event, arg):
    events.append((frame.f_code.co_name, event))
    return tracer


def traced_add(n):
    sys.settrace(tracer)
    try:
        for _ in range(n):
            add(1, 2)
    finally:
        sys.settrace(None)
    return len(events)


show("trace call events", lambda: traced_add(3))
show("value after tracing", lambda: add(1, 2))
print(f"{'sys.implementation':34s} {sys.implementation.name} {sys.version_info[:3]}")
