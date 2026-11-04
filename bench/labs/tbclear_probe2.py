"""Channel test: can we even SEE the traceback cycle die, and where is the crash?

1) gc.get_objects() membership for tracebacks
2) finalization sentinel held by a cycled frame
3) depth at which a long tb_next chain in a cycle kills the process
"""

import gc
import sys


def count_tb_instances():
    tb_type = type(_tb())
    n = 0
    for obj in gc.get_objects():
        if type(obj) is tb_type:
            n += 1
    return n


def _tb():
    try:
        raise ValueError("x")
    except ValueError as e:
        return e.__traceback__


def sentinel_test():
    dead = []

    class Sentinel:
        def __del__(self):
            dead.append("sentinel")

    def build():
        def inner():
            raise ValueError("boom")

        sent = Sentinel()
        try:
            inner()
        except ValueError as exc:
            keep = exc  # local of build(); build frame is tb[0].tb_frame -> cycle
            return keep, id(sent)
        return None, None

    obj, ident = build()
    ref_count_before = count_tb_instances()
    gc.collect()
    gc.collect()
    obj = None
    gc.collect()
    print("  sentinel __del__ fired:", dead)
    print("  traceback objects in gc.get_objects():", ref_count_before)
    return dead


def main():
    print("interpreter:", sys.version.split()[0], sys.implementation.name)
    print("gc.get_objects length:", len(gc.get_objects()))
    print("one live tb counted?:", count_tb_instances())
    print("has __del__ support:", hasattr(object(), "__del__"))
    sentinel_test()


if len(sys.argv) > 1 and sys.argv[1] == "depth":
    depth = int(sys.argv[2]) if len(sys.argv) > 2 else 200000
    print("building chain of", depth, "inside a cycle")

    def inner():
        raise ValueError("boom")

    def build(n):
        exc = None
        for _ in range(n):
            try:
                inner()
            except ValueError as e:
                exc = e
        # exc is a local of build; build's frame is tb[0].tb_frame -> cycle,
        # and the chain hanging off it is n links long.
        return exc

    e = build(depth)
    print("chain built; nodes=", depth, "calling gc.collect()")
    n = gc.collect()
    print("gc.collect returned", n)
    e = None
    print("dropped last ref")
    gc.collect()
    print("survived")
elif len(sys.argv) > 1 and sys.argv[1] == "nocycle":
    depth = int(sys.argv[2]) if len(sys.argv) > 2 else 200000

    def inner():
        raise ValueError("boom")

    def build(n):
        exc = None
        for _ in range(n):
            try:
                inner()
            except ValueError as e:
                exc = e
        return exc.__traceback__

    tb = build(depth)
    print("nocycle chain built, nodes=", depth)
    tb = None
    print("dropped ref (refcount path)")
    gc.collect()
    print("survived")
else:
    main()
