"""Fidelity transcript for the interpreter's `str.split` descriptor kernel.

`CallMethodDescriptorFast` now calls `PyStr::split` itself when the receiver and
the separator on the stack are both exact `str` and exactly one positional
argument was given. That skips the owned argument vector, the second binding of
`sep`, and the `Vec` the list is copied out of - and it also skips the call
context the generic route installs. This file prints everything a caller could
actually observe, so the two routes can be diffed as text:

    rustpython                       bench/labs/test_split_kernel.py > a.txt
    LUNA_ABLATE=splarm rustpython    bench/labs/test_split_kernel.py > b.txt
    diff a.txt b.txt                     # must be empty

The same transcript is what CPython should produce, so run it there too.
Shapes that must NOT reach the kernel are here on purpose: zero and two
positional arguments, a keyword, a maxsplit, a subclass receiver, a non-string
separator, an empty separator, and an error raised inside a traced frame.

    bench/labs/cp314/python.exe       bench/labs/test_split_kernel.py
"""

import sys


def show(label, fn):
    try:
        value = fn()
    except BaseException as exc:  # noqa: BLE001 - the transcript wants any error
        import traceback

        frames = traceback.format_exception_only(type(exc), exc)
        line = frames[0].rstrip("\n")
        print(f"{label}: RAISED {line}")
        return
    print(f"{label}: {value!r}")


s = "a,b,,c"
sub = "ab"
empty = ""


class SubStr(str):
    def __str__(self):
        return "SUB"


ss = SubStr("x,y")

show("plain", lambda: s.split(","))
show("absent sep", lambda: s.split("z"))
show("absent identity", lambda: s.split("z")[0] is s)
show("empty sep", lambda: s.split(""))
show("empty receiver", lambda: empty.split(","))
show("empty piece is singleton", lambda: s.split(",")[2] is "")
show("maxsplit 1", lambda: s.split(",", 1))
show("maxsplit 0", lambda: s.split(",", 0))
show("maxsplit -1 explicit", lambda: s.split(",", -1))
show("keyword sep", lambda: s.split(sep=","))
show("keyword both", lambda: s.split(sep=",", maxsplit=1))
show("two positional", lambda: s.split(",", 2))
show("three positional", lambda: s.split(",", 2, 3))
show("bad sep type", lambda: s.split(1))
show("bad maxsplit type", lambda: s.split(",", "x"))
show("subclass", lambda: list(SubStr("x,y").split(",")))
show("subclass type", lambda: type(SubStr("x,y").split(",")[0]).__name__)
show("substr self", lambda: sub.split(sub))
show("sep longer than receiver", lambda: s.split("abcdefghij"))
show("unicode", lambda: "é,è".split(","))
show("unicode sep", lambda: "aéb".split("é"))
show("many pieces", lambda: ",".join(["a"] * 50).split(",").__len__())
show("leading sep", lambda: ",a".split(","))
show("trailing sep", lambda: "a,".split(","))
show("only sep", lambda: ",".split(","))
show("list identity fresh", lambda: s.split(",") is s.split(","))
show("elem refcount after drop", lambda: (lambda p: (sys.getrefcount(p) > 2))(s.split(",")))


# Errors must still surface through a try/except in the same frame, with the
# value stack left consistent for what runs after the handler.
def recover():
    out = []
    for attempt in range(3):
        try:
            out.append(s.split("" if attempt == 1 else ","))
        except ValueError as exc:
            out.append(f"ValueError {exc}")
    return out


show("recovery after error", recover)


def with_trace():
    events = []

    def tracer(frame, reason, arg):
        events.append((reason, frame.f_code.co_name))
        return tracer

    def inner():
        try:
            return "a,b".split(",")
        except ValueError:
            return None

    sys.settrace(tracer)
    try:
        result = inner()
    finally:
        sys.settrace(None)
    return result, sorted(set(events))


show("trace events", with_trace)


def exc_carry():
    # The separator error inside an active exception must chain the same way.
    try:
        try:
            "a,b".split("")
        except ValueError as first:
            raise RuntimeError("outer") from first
    except RuntimeError as exc:
        return type(exc.__cause__).__name__, str(exc.__cause__)
    return "no error"


show("exception chaining", exc_carry)
