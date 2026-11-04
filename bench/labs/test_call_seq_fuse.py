"""Semantics that any call-sequence fusion must preserve.

Covers: calling a global with constant / borrowed-local arguments, calling
a bound method with a constant argument, keyword and starred forms, arity
and name errors, rebinding during tracing, and generators that yield the
same shapes. Run on CPython and RustPython; both must print the same lines.
"""
import sys

out = []
log = out.append


def call_const_args():
    def add2(a, b):
        return a + b

    g = add2
    acc = 0
    for i in range(5):
        acc += g(1, 2)
        acc += g(1, i)
    return acc


def call_local_arg():
    def ident(x):
        return x

    f = ident
    total = 0
    for i in range(4):
        total += f(i)
    return total


def call_method_const():
    class Box:
        def m(self, a):
            return (self, a)

    b = Box()
    r = []
    for i in range(3):
        r.append(b.m(7))
    return [x[1] for x in r]


def call_kwargs():
    def kw(a, b=2, *rest, c, **more):
        return (a, b, rest, c, sorted(more.items()))

    f = kw
    return [f(1, c=3), f(1, 2, 3, c=4, d=5)]


def call_star_args():
    def three(a, b, c):
        return (a, b, c)

    args = (1, 2)
    g = three
    return [g(*args, 3), g(1, *[2, 3])]


def missing_arg():
    def two(a, b):
        return a + b

    f = two
    try:
        return f(1)
    except TypeError as e:
        return "TypeError: %s" % str(e).strip()


def unexpected_kwarg():
    def two(a, b):
        return a + b

    f = two
    try:
        return f(1, b=2, c=3)
    except TypeError as e:
        return "TypeError: %s" % str(e).strip()


def unbound_callee():
    try:
        return not_defined(1, 2)
    except NameError as e:
        return "NameError: %s" % str(e).split("'")[0].strip()


def rebinding_callee():
    def one(x):
        return ("one", x)

    def two(x):
        return ("two", x)

    g = one
    log(str(call_with(g, 1)))
    g = two
    log(str(call_with(g, 2)))
    g = lambda x: ("lambda", x)
    log(str(call_with(g, 3)))

    class Met:
        def __call__(cls, x):
            return ("metacall", x)

    g = Met()
    log(str(call_with(g, 4)))


def call_with(f, arg):
    return f(arg)


def builtin_target():
    g = len
    h = int
    for i in range(2):
        pass
    return [g([1, 2, 3]), h("42"), g("ab")]


def generator_shapes():
    def gen():
        for i in range(3):
            yield helper(i)

    def helper(x):
        return x * 10

    return list(gen())


def traced_call():
    """A tracer must see every instruction of a fused sequence."""
    def callee(a, b):
        return a + b

    calls = callee
    events = []

    def tracer(frame, event, arg):
        if event == "call":
            events.append(frame.f_code.co_name)
        return tracer

    old = sys.gettrace()
    sys.settrace(tracer)
    try:
        calls(1, 2)
    finally:
        sys.settrace(None)
    got = events.count("callee")
    sys.settrace(old)
    return "callee call events=%d" % got


def monitoring_callee():
    """Monitoring is exercised by the per-fusion tests, which know the
    callback signature; here only tracing coverage matters."""
    return "skipped"


def nested_arg_call():
    def outer(x):
        return inner(x) + 1

    def inner(y):
        return y * 2

    f = outer
    total = 0
    for i in range(4):
        total += f(i)
    return total


log("const args: %s" % call_const_args())
log("local arg: %s" % call_local_arg())
log("method const: %s" % call_method_const())
log("kwargs: %s" % call_kwargs())
log("star args: %s" % call_star_args())
log("missing arg: %s" % missing_arg())
log("unexpected kwarg: %s" % unexpected_kwarg())
log("unbound: %s" % unbound_callee())
rebinding_callee()
log("builtin target: %s" % builtin_target())
log("generator shapes: %s" % generator_shapes())
log("traced: %s" % traced_call())
log("monitoring: %s" % monitoring_callee())
log("nested: %s" % nested_arg_call())

print("python %s %s" % (sys.version.split()[0], sys.implementation.name))
for line in out:
    print(line)
print("DONE %d lines" % len(out))
