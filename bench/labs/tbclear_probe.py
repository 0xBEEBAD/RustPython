"""Facts about exception/traceback cycles, measured on the reference first.

Run on cp314 and on RustPython; no assertions, only prints, so the two
interpreters' answers can be compared before a parity test is written.
"""

import gc
import sys


def weakref_target(obj, label):
    try:
        import weakref

        return weakref.ref(obj)
    except TypeError as exc:
        print(f"  weakref({label}) unsupported: {exc}")
        return None


def build_cycle():
    """Create exc <-> tb <-> frame cycle, return refs that die with the cycle."""

    def inner():
        raise ValueError("boom")

    refs = []
    try:
        inner()
    except ValueError as exc:
        # `exc` is a local of this frame, and this frame is kept alive by
        # exc.__traceback__.tb_frame -- that is the cycle.
        tb = exc.__traceback__
        refs.append(("exc", weakref_target(exc, "exception")))
        refs.append(("tb", weakref_target(tb, "traceback")))
        refs.append(("frame", weakref_target(tb.tb_frame, "frame")))
        refs.append(("tracked_tb", gc.is_tracked(tb)))
        refs.append(("tracked_frame", gc.is_tracked(tb.tb_frame)))
    return refs


def main():
    print("interpreter:", sys.version.split()[0], sys.implementation.name)

    refs = build_cycle()
    by_name = dict(refs)
    print("gc.is_tracked(traceback):", by_name.get("tracked_tb"))
    print("gc.is_tracked(frame):", by_name.get("tracked_frame"))

    collected = gc.collect()
    print("gc.collect() returned:", collected)
    for name in ("exc", "tb", "frame"):
        ref = by_name.get(name)
        if ref is not None:
            print(f"  after collect, {name} alive:", ref() is not None)

    # second pass, in case the first only broke the outer link
    gc.collect()
    for name in ("exc", "tb", "frame"):
        ref = by_name.get(name)
        if ref is not None:
            print(f"  after collect2, {name} alive:", ref() is not None)

    # uncollectable garbage, if the interpreter reports it at all
    garbage = getattr(gc, "garbage", None)
    print("len(gc.garbage):", len(garbage) if garbage is not None else "no gc.garbage")

    # does __traceback__ get cleared out of the exception on collection?
    e = ValueError("x")
    eref = weakref_target(e, "plain exception")
    e = None
    gc.collect()
    print("plain exception alive after collect:", eref() is not None if eref else "n/a")


main()
