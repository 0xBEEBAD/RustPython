"""Parity test for tracebacks of StopAsyncIteration thrown into async generators.

PEP 525: when a Stop(Async)Iteration is thrown into an (async) generator and
escapes unchanged, CPython keeps the traceback the exception had when throw()
was called; the generator and athrow frames are not appended. Exceptions
raised inside the generator body keep their generator frame.

  python test_asyncgen_throw_tb.py
  rustpython test_asyncgen_throw_tb.py
"""
import asyncio
import sys
import traceback
from contextlib import asynccontextmanager, contextmanager

failures = 0


def check(name, got, want):
    global failures
    if got == want:
        print(f"PASS {name}")
    else:
        failures += 1
        print(f"FAIL {name}: got {got!r}, want {want!r}")


@asynccontextmanager
async def f():
    yield


class StopAsyncIterationSubclass(StopAsyncIteration):
    pass


async def throw_into_asyncgen():
    for stop_exc in (StopAsyncIteration("ham"), StopAsyncIterationSubclass("spam")):
        try:
            async with f():
                raise stop_exc
        except type(stop_exc) as e:
            check(f"{type(stop_exc).__name__} identity", e is stop_exc, True)
            frames = traceback.extract_tb(e.__traceback__)
            check(f"{type(stop_exc).__name__} frame count", len(frames), 1)
            check(
                f"{type(stop_exc).__name__} frame name",
                frames[0].name if frames else None,
                "throw_into_asyncgen",
            )
            check(
                f"{type(stop_exc).__name__} frame line",
                frames[0].line if frames else None,
                "raise stop_exc",
            )
        else:
            check(f"{type(stop_exc).__name__} propagated", False, True)


@asynccontextmanager
async def raises_inside():
    yield
    raise KeyError("inside")


async def raise_inside_asyncgen():
    try:
        async with raises_inside():
            pass
    except KeyError as e:
        frames = traceback.extract_tb(e.__traceback__)
        check("inside-gen has generator frame", frames[-1].name, "raises_inside")
        check("inside-gen keeps frames", len(frames) >= 2, True)


@contextmanager
def sync_raises_inside():
    yield
    raise KeyError("inside")


def raise_inside_syncgen():
    try:
        with sync_raises_inside():
            pass
    except KeyError as e:
        frames = traceback.extract_tb(e.__traceback__)
        check("sync inside-gen keeps generator frame", frames[-1].name, "sync_raises_inside")


def body_raise_keeps_original():
    exc = ValueError("body")
    try:
        with contextmanager(lambda: (yield))():
            raise exc
    except ValueError as e:
        check("sync body raise identity", e is exc, True)
        check("sync body raise frames", len(traceback.extract_tb(e.__traceback__)), 1)


asyncio.run(throw_into_asyncgen())
asyncio.run(raise_inside_asyncgen())
raise_inside_syncgen()
body_raise_keeps_original()

print("RESULT", "FAIL" if failures else "OK")
sys.exit(1 if failures else 0)
