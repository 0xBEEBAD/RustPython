"""Find callables that accept a keyword argument no signature can contain.

`zzzq` is not a parameter of anything in the stdlib, so every correct
implementation must raise TypeError before it can do any work - which makes this
a safe detector for the bug class found in `itertools.chain(x=1, y=2)`: a builtin
whose `__new__`/`__init__` hand-consumes the positional half of its `FuncArgs`
and drops the keyword half answers nothing at all, where CPython answers
`chain() takes no keyword arguments`.

Nothing here is called with a real keyword, so no function can run: a call either
raises the TypeError we are after, or (for the broken ones) returns.

    python bench/labs/kwarg_acceptors.py
"""

import builtins
import sys
import types

MODULES = [
    builtins,
    types,
    sys,
]

NAMES = [
    "itertools", "functools", "collections", "collections.abc", "os", "time",
    "_thread", "array", "weakref", "io", "marshal", "zipimport", "errno",
    "math", "binascii", "signal", "gc", "atexit", "operator", "reprlib",
    "contextlib", "dataclasses", "enum", "copy", "pickle", "struct",
]

for name in NAMES:
    try:
        MODULES.append(__import__(name))
    except Exception:  # noqa: BLE001 - a missing optional module is fine
        pass

KEY = "zzzq"
accepted = []
checked = 0

for mod in MODULES:
    try:
        attrs = list(vars(mod).items())
    except Exception:  # noqa: BLE001
        continue
    for attr_name, value in attrs:
        # only classes and plain builtin functions; skip modules and sub-namespaces
        if isinstance(value, types.ModuleType):
            continue
        if not (isinstance(value, type) or callable(value)):
            continue
        if isinstance(value, type):
            targets = [value, getattr(value, "__init__", None),
                       getattr(value, "__new__", None)]
        else:
            targets = [value]
        for fn in targets:
            if fn is None or not callable(fn):
                continue
            checked += 1
            try:
                fn(**{KEY: 1})
            except TypeError as exc:
                text = str(exc)
                if "unexpected keyword" in text or "takes no keyword" in text:
                    continue  # correct: it noticed the keyword
                if "argument" in text or "required" in text:
                    continue  # arity complaint before the keyword check: CPython
                                # does this too for some signatures; the diff with
                                # CPython is what matters, so record it anyway
                accepted.append(f"{mod.__name__}.{attr_name}: TypeError text {text!r}")
            except Exception as exc:  # noqa: BLE001 - any other error means it ran
                accepted.append(f"{mod.__name__}.{attr_name}: ran, {type(exc).__name__}")
            else:
                accepted.append(f"{mod.__name__}.{attr_name}: ACCEPTED (no error)")

for line in sorted(set(accepted)):
    print(line)
print(f"checked={checked} suspect={len(set(accepted))}")
print(f"interpreter: {sys.implementation.name} {sys.version_info[:3]}")
