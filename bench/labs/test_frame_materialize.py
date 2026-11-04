"""Behavior pinned to frames materialized by a traceback (the escape path).

Every row is printed as `label -> value`, so the same file run on CPython and
RustPython can be diffed directly. These are the semantics that a cheaper
materialization must not break: f_locals of the raising frame while the except
clause runs, identity of tb_frame across accesses, f_back walkability after the
ancestors returned, frame.clear() on an escaped frame, and what a cycle
collector sees.

    python bench/labs/test_frame_materialize.py
"""
import gc
import sys


def show(label, fn):
    try:
        print(f"{label:34s} -> {fn()!r}")
    except Exception as exc:
        print(f"{label:34s} -> {type(exc).__name__}: {exc}")


def inner(x=1, y=2):
    z = x + y
    raise ValueError("boom")


def middle():
    return inner()


def outer():
    try:
        middle()
    except ValueError as exc:
        tb = exc.__traceback__
        f = tb.tb_frame
        # walk to the innermost entry
        while tb.tb_next:
            tb = tb.tb_next
        g = tb.tb_frame
        return {
            "outer_locals": sorted(f.f_locals),
            "inner_locals": sorted(g.f_locals),
            "identity": g is tb.tb_frame,
            "names": (f.f_code.co_name, g.f_code.co_name),
            "back_name": (g.f_back or f).f_code.co_name if g.f_back else None,
            "lineno": (f.f_lineno, g.f_lineno),
            "exc": exc,
        }


result = outer()
show("outer frame locals", lambda: result["outer_locals"])
show("inner frame locals", lambda: result["inner_locals"])
show("tb_frame identity", lambda: result["identity"])
show("code names", lambda: result["names"])
show("f_back name", lambda: result["back_name"])
show("line numbers", lambda: result["lineno"])

exc = result["exc"]
tb = exc.__traceback__
inner_frame = tb
while inner_frame.tb_next:
    inner_frame = inner_frame.tb_next
inner_frame = inner_frame.tb_frame

show("inner locals after return", lambda: sorted(inner_frame.f_locals))
show("inner f_back after return", lambda: inner_frame.f_back is None)
show("frame.clear exists", lambda: hasattr(inner_frame, "clear"))
show("frame.clear result", lambda: inner_frame.clear())
show("locals after clear", lambda: sorted(inner_frame.f_locals))


def gen_frames():
    """A generator that raises, so the frame is also owned by a generator."""

    def g():
        local = 5
        yield 1
        raise RuntimeError("gen")

    it = g()
    next(it)
    try:
        it.send(None)
    except RuntimeError as exc:
        return exc.__traceback__.tb_frame.f_locals


show("generator raise locals", lambda: sorted(gen_frames()))


def cycle_with_traceback():
    class Box:
        pass

    b = Box()
    try:
        raise ValueError("cycle")
    except ValueError as exc:
        b.exc = exc
        exc.__traceback__.tb_frame.f_locals  # touch the materialized frame
        del exc
    gc.collect()
    return type(b.exc).__name__, b.exc.__traceback__ is not None


show("traceback cycle survives gc", lambda: cycle_with_traceback())
show("getframe identity", lambda: sys._getframe() is sys._getframe())
print(f"{'implementation':34s} -> {sys.implementation.name} {sys.version_info[:3]}")
