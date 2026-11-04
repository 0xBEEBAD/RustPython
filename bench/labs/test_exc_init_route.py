"""Pin what a class call does when `__new__` and `__init__` both consume the args.

The type-call path in `crates/vm/src/builtins/type.rs` skips `__init__` for the
builtin exception types, because `BaseException.__new__` already stores `args`
and `BaseException.__init__` adds nothing but the keyword rejection that cannot
fire on a keyword-free call. That is only sound if the skip is limited to that
exact new/init pair, so every case that could be confused with it is printed
here: classes with their own initializers, subclasses that rebind `__init__` to
the base one, `__new__` that returns a different class, and ordinary non-
exception classes.

Run on both interpreters and diff:

    python bench/labs/test_exc_init_route.py
"""

import sys


def show(label, fn):
    try:
        value = fn()
    except BaseException as exc:
        print(f"{label:34s} {type(exc).__name__}: {exc}")
    else:
        print(f"{label:34s} {value!r}")


def describe(exc):
    return (exc.args, getattr(exc, "name", None), getattr(exc, "obj", None),
            getattr(exc, "errno", None), repr(str(exc)))


class Plain:
    def __init__(self, x):
        self.x = x


class WithNew:
    def __new__(cls, x):
        obj = super().__new__(cls)
        obj.made = x
        return obj

    def __init__(self, x):
        self.init_ran = x


class Other(WithNew):
    pass


class Sub(Exception):
    pass


class SubOfSub(Sub):
    pass


class OwnInit(Exception):
    def __init__(self, code):
        self.code = code * 2

    def __new__(cls, code):
        obj = super().__new__(cls, code)
        return obj


class KwargsInit(Exception):
    def __init__(self, *, tag):
        self.tag = tag


class ReboundInit(Exception):
    __init__ = BaseException.__init__


class NewReturnsOther(Exception):
    def __new__(cls, *a):
        return Sub("swapped")


class InitReturns(Exception):
    def __init__(self, x):
        self.x = x
        return None


class SubOfValueError(ValueError):
    pass


show("ValueError()", lambda: ValueError().args)
show("ValueError('boom')", lambda: ValueError("boom").args)
show("Exception('a', 'b')", lambda: Exception("a", "b").args)
show("BaseException('x')", lambda: BaseException("x").args)
show("ValueError(x=1)", lambda: ValueError(x=1))
show("BaseException(x=1)", lambda: BaseException(x=1))
show("Exception('a', k=1)", lambda: Exception("a", k=1))
show("AttributeError('m')", lambda: describe(AttributeError("m")))
show("AttributeError('m', name='n', obj='o')",
     lambda: describe(AttributeError("m", name="n", obj="o")))
show("AttributeError('m', 'n')", lambda: describe(AttributeError("m", "n")))
show("OSError(2, 'msg')", lambda: describe(OSError(2, "msg")))
show("OSError(2, 'msg', filename='f')",
     lambda: describe(OSError(2, "msg", filename="f")))
show("UnicodeDecodeError args", lambda: describe(
    UnicodeDecodeError("utf-8", b"\\xff", 0, 1, "bad")))
show("TypeError() args", lambda: TypeError().args)
show("Sub('boom')", lambda: Sub("boom").args)
show("SubOfSub('boom')", lambda: SubOfSub("boom").args)
show("Sub(x=1)", lambda: Sub(x=1))
show("OwnInit(3)", lambda: (OwnInit(3).code, OwnInit(3).args))
show("OwnInit(x=1)", lambda: OwnInit(x=1))
show("KwargsInit(tag='t')", lambda: (KwargsInit(tag="t").tag, KwargsInit(tag="t").args))
show("ReboundInit('boom')", lambda: ReboundInit("boom").args)
show("ReboundInit(x=1)", lambda: ReboundInit(x=1))
show("NewReturnsOther('a')", lambda: (type(NewReturnsOther("a")).__name__,
                                     NewReturnsOther("a").args))
show("InitReturns(1) attrs", lambda: (InitReturns(1).x, InitReturns(1).args))
show("SubOfValueError('boom')", lambda: SubOfValueError("boom").args)
show("Plain(1).x", lambda: Plain(1).x)
show("WithNew('w').both", lambda: (WithNew("w").made, WithNew("w").init_ran))
show("Other('w').both", lambda: (Other("w").made, Other("w").init_ran))
show("class with only __new__", lambda: (
    type("OnlyNew", (), {"__new__": lambda cls: 42})(),
))
show("dict([('a', 1)])", lambda: dict([("a", 1)]))
show("str(123)", lambda: str(123))
show("int('10', 2)", lambda: int("10", 2))
show("tuple(1 for _ in (1, 2))", lambda: tuple(i for i in (1, 2)))
show("type('X', (), {})()", lambda: type("X", (), {})().__class__.__name__)
show("type('X', (), {'__init__': lambda s, y: None})(1).x",
     lambda: hasattr(type("X", (), {"__init__": lambda s, y: None})(1), "x"))
show("type(1)", lambda: type(1))
show("type('a', 'b', 'c')", lambda: type("Y", (), {}) is not None)
show("StopIteration('v').value", lambda: (StopIteration("v").args, StopIteration("v").value))
show("SystemExit('v').code", lambda: (SystemExit("v").args, SystemExit("v").code))
show("SystemExit(1, 2)", lambda: SystemExit(1, 2).args)
show("ExceptionGroup('e', [])", lambda: (
    ExceptionGroup("e", []).args, len(ExceptionGroup("e", []).exceptions)))
show("subclass of OSError", lambda: (
    type("OSErr", (OSError,), {})("boom").args,
    type("OSErr", (OSError,), {})("boom").errno))
show("subclass of OSError(2, 'm')", lambda: (
    type("OSErr", (OSError,), {})(2, "m").args,
    type("OSErr", (OSError,), {})(2, "m").errno))
show("rebound __init__ on heap subclass", lambda: (
    type("E", (Exception,), {"__init__": BaseException.__init__})("z").args))
show("init set to object.__init__", lambda: (
    type("E", (Exception,), {"__init__": object.__init__})("z").args))
print(f"{'sys.version_info':34s} {sys.version_info[:3]}")
