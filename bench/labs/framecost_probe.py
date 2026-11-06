"""Decompose the ~77 ns a frame activation costs, using the LUNA_ABLATE ladder.

The three first rows are bench/labs/genstep.py's shapes, so their live numbers
are directly comparable; the fourth is genstep's "call per item" with the
result discarded. That row exists because the measurement bits `armstage` and
`stubcall` answer the call with `None`, and `total += None` raises TypeError --
a discarded result is legal whatever the callee is stubbed to return, so the
ladder reads off one binary without the probe dying.

The callee is built once by `_mk` and handed to the callers as a default
argument, so both call rows load it with LOAD_FAST (like genstep's nested
`inner`) and share one qualname for `LUNA_STUB_BODY` to match.

Ladder (names defined in crates/vm/src/perf_debug.rs; see bench/labs/armprice.sh
for the same idea on callfloor.py):

  live                                            dispatch + guards + stage + frame + body
  LUNA_STUB_BODY=_mk.<locals>._zzip               callee frame entered, body skipped
  ... LUNA_ABLATE=armstage                        stops after arg staging: no callee frame
  ... LUNA_ABLATE=stubcall                        stops inside invoke_exact_args_slots
  LUNA_ABLATE=notail                              recursive entry, not the TailCall trampoline
  LUNA_ABLATE=armguards                           + skip the eligibility guards (drops tailcall too)
  LUNA_ABLATE=frameless                           exact-args call via a materialized FrameObject
  LUNA_ABLATE=exitclone                           clone the return value at every frame exit

Subtracting neighbours prices exactly the code the second row turns off.
N is 1,000,000 and best of 5, like genstep.py.
"""
import time

N = 1_000_000
RUNS = 5


def _mk():
    def _zzip(i):
        return i
    return _zzip


_zzip = _mk()


def zzgen(n):
    for i in range(n):
        yield i


def gen_step(n):
    g = zzgen(n)
    total = 0
    for value in g:
        total += value
    return total


def plain_loop(n):
    total = 0
    for i in range(n):
        total += i
    return total


def call_per_item(n, f=_zzip):
    total = 0
    for i in range(n):
        total += f(i)
    return total


def call_stmt(n, f=_zzip):
    for i in range(n):
        f(i)


def call_nested(n):
    # genstep.py's exact shape: the callee is defined inside the timed function
    # and loaded with LOAD_FAST, so this row cross-checks `call per item` there.
    def inner(i):
        return i
    total = 0
    for i in range(n):
        total += inner(i)
    return total


def timeit(fn, iters, runs=RUNS):
    best = float("inf")
    for _ in range(runs):
        start = time.perf_counter()
        fn(iters)
        best = min(best, time.perf_counter() - start)
    return best


for label, fn in (("gen step", gen_step), ("plain loop", plain_loop),
                  ("call per item", call_per_item), ("call stmt", call_stmt),
                  ("call nested", call_nested)):
    try:
        seconds = timeit(fn, N)
    except TypeError as exc:
        print(f"{label:16s} n/a ({exc})")
        continue
    print(f"{label:16s} {N / seconds / 1e6:8.3f} M ops/s   {seconds / N * 1e9:7.1f} ns/op")
