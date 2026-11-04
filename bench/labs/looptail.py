"""Behavior of loop tails after the POP_TOP + JUMP_BACKWARD fusion.

Each case runs a loop whose last statement discards a value - the shape the
fusion folds into one dispatch - and checks the call count, the exception
paths that cross a fused tail, and a backedge wide enough that the distance
needs an EXTENDED_ARG (which the fused instruction must refuse to swallow).

    python bench/labs/looptail.py

Prints one line per case; the numbers must match CPython's exactly.
"""


def count_discards(n):
    calls = []

    def g():
        calls.append(1)

    i = 0
    while i < n:
        i += 1
        g()
    return len(calls)


def count_for_discards(n):
    calls = []

    def g(x):
        calls.append(x)

    for x in range(n):
        g(x)
    return len(calls)


def exception_across_tail(n):
    # The tail call raises on the last iteration only: unwinding has to work
    # from a fused POP_TOP; JUMP_BACKWARD as well as from the split pair.
    calls = []
    caught = []

    def g(i):
        calls.append(i)
        if i == n - 1:
            raise ValueError(i)

    try:
        for i in range(n):
            g(i)
    except ValueError as exc:
        caught.append(exc.args[0])
    return len(calls), caught


def wide_backedge(n):
    # More code units between the loop header and its tail than one arg byte
    # can carry, so the distance travels through an EXTENDED_ARG.
    calls = []
    a0 = a1 = a2 = a3 = a4 = 0
    a5 = a6 = a7 = a8 = a9 = 0
    b0 = b1 = b2 = b3 = b4 = 0
    b5 = b6 = b7 = b8 = b9 = 0

    def g():
        calls.append(1)

    i = 0
    while i < n:
        a0 = a0 + 1
        a1 = a1 + 2
        a2 = a2 + 3
        a3 = a3 + 4
        a4 = a4 + 5
        a5 = a5 + 6
        a6 = a6 + 7
        a7 = a7 + 8
        a8 = a8 + 9
        a9 = a9 + 10
        b0 = b0 + 11
        b1 = b1 + 12
        b2 = b2 + 13
        b3 = b3 + 14
        b4 = b4 + 15
        b5 = b5 + 16
        b6 = b6 + 17
        b7 = b7 + 18
        b8 = b8 + 19
        b9 = b9 + 20
        a0 = a0 + 1
        a1 = a1 + 2
        a2 = a2 + 3
        a3 = a3 + 4
        a4 = a4 + 5
        a5 = a5 + 6
        a6 = a6 + 7
        a7 = a7 + 8
        a8 = a8 + 9
        a9 = a9 + 10
        b0 = b0 + 11
        b1 = b1 + 12
        b2 = b2 + 13
        b3 = b3 + 14
        b4 = b4 + 15
        b5 = b5 + 16
        b6 = b6 + 17
        b7 = b7 + 18
        b8 = b8 + 19
        b9 = b9 + 20
        i += 1
        g()
    return len(calls), a0 + b9


def nested_tails(n):
    calls = []

    def g():
        calls.append(1)

    for _ in range(n):
        for _ in range(3):
            g()
    return len(calls)


def traced_tail(n):
    # A tracer has to keep seeing the swallowed JUMP_BACKWARD: count opcode
    # events over the loop and make sure the loop still terminates.
    events = []

    def tracer(frame, event, arg):
        if event == "call":
            frame.f_trace_opcodes = True
            return tracer
        if event == "opcode":
            events.append(frame.f_lineno)
        return tracer

    import sys

    calls = []

    def g():
        calls.append(1)

    def run():
        i = 0
        while i < n:
            i += 1
            g()
        return i

    sys.settrace(tracer)
    try:
        result = run()
    finally:
        sys.settrace(None)
    return len(calls), result, len(events) > 0


CASES = [
    ("while discard", lambda: count_discards(300)),
    ("for discard", lambda: count_for_discards(200)),
    ("exc across tail", lambda: exception_across_tail(50)),
    ("wide backedge", lambda: wide_backedge(100)),
    ("nested tails", lambda: nested_tails(40)),
    ("traced tail", lambda: traced_tail(20)),
]

for name, fn in CASES:
    print(f"{name:18s} {fn()}")
