"""Does the exception<->traceback<->frame cycle actually get released today?

Build N such cycles, drop every Python reference, gc.collect(), then count the
traceback objects still reachable through gc.get_objects(). CPython's tb_clear
breaks the cycle, so the count returns to the baseline; a payload whose tp_clear
is missing keeps the chain alive.
"""

import gc
import sys


def tb_count():
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


def make_cycles(n):
    def inner():
        raise ValueError("boom")

    for _ in range(n):
        try:
            inner()
        except ValueError as exc:
            # `exc` is a local of make_cycles; make_cycles' frame is
            # exc.__traceback__.tb_frame -> a real reference cycle.
            pass
    return n


def main(n):
    print("interpreter:", sys.version.split()[0], sys.implementation.name)
    gc.collect()
    baseline = tb_count()
    print("baseline traceback objects:", baseline)
    made = make_cycles(n)
    print("cycles made:", made)
    gc.collect()
    gc.collect()
    after = tb_count()
    print("traceback objects after collect:", after)
    print("leaked:", after - baseline)
    print("objects total after collect:", len(gc.get_objects()))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2000)
