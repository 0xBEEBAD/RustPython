"""Allocation census for the raise chain: how many heap blocks does one
call+raise+catch actually move through, on each interpreter.

Read sys.getallocatedblocks() across a fixed number of raise ops, with the
exception objects kept alive and with them released, so the census separates
"blocks created per raise" from "blocks left behind per raise".

    rp-lite-119.exe bench/labs/rp_exc_alloc.py
    cp314/python.exe bench/labs/rp_exc_alloc.py
"""
import sys


def throw(i):
    raise ValueError(i)


def keep(n, sink):
    for i in range(n):
        try:
            throw(i)
        except ValueError as e:
            sink.append(e.__traceback__)


def drop_all(n):
    for i in range(n):
        try:
            throw(i)
        except ValueError:
            pass


def floor(n):
    for i in range(n):
        pass


def census(name, fn, keepalive=False):
    sink = [] if keepalive else None
    fn(1000, sink) if keepalive else fn(1000)
    base = sys.getallocatedblocks()
    N = 2000
    fn(N, sink) if keepalive else fn(N)
    after = sys.getallocatedblocks()
    print("%-22s %+10d blocks / %5d ops = %6.2f blocks per op"
          % (name, after - base, N, (after - base) / N))


print("# %s %s" % (sys.implementation.name, ".".join(map(str, sys.version_info[:3]))))
print("# baseline loop floor")
census("floor", floor)
census("raise kept(tb alive)", keep, keepalive=True)
census("raise dropped", drop_all)
try:
    print("getallocatedblocks supported:", sys.getallocatedblocks())
except Exception as e:  # noqa: BLE001
    print("no getallocatedblocks:", e)
