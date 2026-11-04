"""Print what every exception-construction shape with keyword arguments does.

`BaseException.__init__` accepts positionals only, but that rule is inherited
differently per type: builtin subclasses reject keywords, subclasses that define
their own `__init__` get the Python-level "unexpected keyword" message, and
OSError / UnicodeDecodeError / StopIteration really do take keywords. The
constructor path and the initializer path are separate in the interpreter, so a
change that fixes one shape can silently break another; this probe prints one
line per shape and is meant to be diffed between CPython and RustPython rather
than read for a verdict.

    python bench/labs/test_exc_kwargs.py
"""

import sys


class Plain(Exception):
    pass


class WithInit(Exception):
    def __init__(self, a=None):
        super().__init__(a)


class FromBase(BaseException):
    pass


def show(text, fn):
    try:
        value = fn()
        print(f"{text:52s} -> OK   args={value.args!r} type={type(value).__name__}")
    except Exception as exc:  # noqa: BLE001 - the error text is the result
        print(f"{text:52s} -> {type(exc).__name__}: {exc}")


cases = [
    ("BaseException(x=1)", lambda: BaseException(x=1)),
    ("Exception(x=1)", lambda: Exception(x=1)),
    ("ValueError(x=1)", lambda: ValueError(x=1)),
    ("KeyError(x=1)", lambda: KeyError(x=1)),
    ("ArithmeticError(x=1)", lambda: ArithmeticError(x=1)),
    ("Exception('a', x=1)", lambda: Exception('a', x=1)),
    ("ValueError(1, x=2)", lambda: ValueError(1, x=2)),
    ("Exception(args=1)", lambda: Exception(args=1)),
    ("Exception(message='m')", lambda: Exception(message='m')),
    ("Plain(x=1)", lambda: Plain(x=1)),
    ("FromBase(x=1)", lambda: FromBase(x=1)),
    ("WithInit(x=1)", lambda: WithInit(x=1)),
    ("WithInit(a=1)", lambda: WithInit(a=1)),
    ("type(Exception).call__", lambda: Exception.__new__(Exception, x=1)),
    ("OSError(1, 'm', filename='f')", lambda: OSError(1, 'm', filename='f')),
    ("OSError(x=1)", lambda: OSError(x=1)),
    ("StopIteration(x=1)", lambda: StopIteration(x=1)),
    ("StopIteration(value=1)", lambda: StopIteration(value=1)),
    ("UnicodeDecodeError('utf8', b'', 0, 1, x=1)",
     lambda: UnicodeDecodeError('utf8', b'', 0, 1, x=1)),
    ("SystemExit(x=1)", lambda: SystemExit(x=1)),
    ("ImportError(name='n')", lambda: ImportError(name='n')),
    ("AttributeError(name='n')", lambda: AttributeError(name='n')),
]

for text, fn in cases:
    show(text, fn)

print(f"interpreter: {sys.implementation.name} {sys.version_info[:3]}")
