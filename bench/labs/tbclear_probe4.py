"""Cycles that CPython breaks in tb_clear, with no exception object involved.

CPython's `tb_clear` (Python/traceback.c) does Py_CLEAR(tb->tb_next) and
Py_CLEAR(tb->tb_frame) and the type advertises tp_clear, so the collector can
cut a cycle that runs purely through traceback -> frame -> locals dict ->
traceback. A payload without tp_clear leaves that cycle uncollectable.

Count traceback objects still in gc.get_objects() after collect(); CPython's
answer is the parity target.
"""

import gc
import sys


def _tb():
    try:
        raise ValueError("x")
    except ValueError as e:
        return e.__traceback__


def tb_count():
    kind = type(_tb())
    n = 0
    for obj in gc.get_objects():
        if type(obj) is kind:
            n += 1
    return n


def inner():
    raise ValueError("boom")


def shape_exception(n):
    """exc -> tb -> frame -> exc (the classic CPython exception cycle)."""
    for _ in range(n):
        try:
            inner()
        except ValueError as exc:
            pass


def shape_box_no_exc(n):
    """tb -> frame -> f_locals dict -> box -> tb, with the exception dropped."""
    for _ in range(n):
        try:
            inner()
        except ValueError as exc:
            tb = exc.__traceback__
            frame_locals = tb.tb_frame.f_locals
            frame_locals["box"] = {"tb": tb}
            exc = None
            tb = None
            frame_locals = None


def run(n):
    print("interpreter:", sys.version.split()[0], sys.implementation.name)
    gc.collect()
    baseline = tb_count()
    print("baseline tracebacks:", baseline)
    for name, shape in (("exception-hub", shape_exception), ("box-without-exception", shape_box_no_exc)):
        shape(n)
        gc.collect()
        gc.collect()
        after = tb_count()
        print(f"  {name}: leaked tracebacks = {after - baseline} (now {after})")
        shape(0)
        gc.collect()
        gc.collect()


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 2000)
