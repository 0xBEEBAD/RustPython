"""Sweep builtin method keyword rejections across types and diff interpreters.

The landed rule is per-message, not per-callable: `takes no keyword arguments`
carries the qualified name (`str.count()`) and `got an unexpected keyword
argument` carries the bare one (`split()`). Each type writes its own argument
parser in C, so one fix cannot cover the surface - this enumerates it
mechanically instead: every public method of a scalar or container type gets
called with a keyword no signature can contain, in both the bound and the
unbound form, and each reply is printed for a byte diff between CPython and
RustPython.

Only the *message* is interesting; every call raises before it can do work, and
all objects are throwaways, which is why file and socket types stay out.

    python bench/labs/kwmsg_sweep.py
"""

import sys

TYPES = [
    str,
    bytes,
    bytearray,
    list,
    dict,
    set,
    frozenset,
    tuple,
    int,
    float,
    complex,
    bool,
    range,
    slice,
    object,
    memoryview,
]

KEY = "zzzq"


def sample_of(t):
    return {
        str: "",
        bytes: b"",
        bytearray: bytearray(),
        list: [],
        dict: {},
        set: set(),
        frozenset: frozenset(),
        tuple: (),
        int: 0,
        float: 0.0,
        complex: 0j,
        bool: False,
        range: range(0),
        slice: slice(0),
        object: object(),
        memoryview: memoryview(b""),
    }[t]


def emit(text, fn):
    # The label can contain a `repr()` of the sample, and objects with an
    # address in their repr (memoryview) would diff as a false divergence.
    import re

    text = re.sub(r"0x[0-9a-fA-F]+", "0xADDR", text)
    try:
        fn()
        print(f"{text} -> NO ERROR")
    except Exception as exc:  # noqa: BLE001 - the message is the whole result
        line = f"{type(exc).__name__}: {exc}"
        # A "Did you mean" suggestion depends on which names the type exposes.
        line = line.split(". Did you mean")[0]
        print(f"{text} -> {line}")


for t in TYPES:
    sample = sample_of(t)
    for name in sorted(n for n in dir(t) if not n.startswith("__")):
        try:
            attr = getattr(t, name)
        except Exception:  # noqa: BLE001 - computed class attributes
            continue
        if not callable(attr):
            continue
        emit(
            f"{t.__name__}.{name}(self, {KEY}=1) unbound",
            lambda n=name, s=sample: getattr(t, n)(s, **{KEY: 1}),
        )
        emit(
            f"{t.__name__}({sample!r}).{name}({KEY}=1) bound",
            lambda n=name: getattr(sample, n)(**{KEY: 1}),
        )

print(f"interpreter: {sys.implementation.name} {sys.version_info[:3]}")
