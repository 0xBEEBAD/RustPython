"""Does a trace callback that moves the frame out from under the dispatch loop
get honored? Covers both events that can fire before the move: 'line' (the case
the interpreter already handled) and 'opcode' (f_trace_opcodes).

    python bench/labs/reposition.py

Prints one line per case: the line the tracer moved from and to, the statements
that actually ran, and whether the middle statement was skipped. `ran` names the
three markers in order, so a missing 'B' proves the frame really moved.
"""

import sys


def target(ran):
    ran.append("A")
    ran.append("B")
    ran.append("C")
    return "done"


FIRST = target.__code__.co_firstlineno + 1  # the ran.append("A") line
MIDDLE = FIRST + 1
LAST = FIRST + 2


def make_tracer(event):
    notes = []

    def tracer(frame, ev, arg):
        if ev == "call":
            if event == "opcode":
                frame.f_trace_opcodes = True
            return tracer
        if ev == event and frame.f_code.co_name == "target":
            if frame.f_lineno == FIRST and not any(n.startswith("moved") for n in notes):
                try:
                    frame.f_lineno = LAST
                    notes.append(f"moved {FIRST}->{LAST}")
                except Exception as exc:
                    notes.append(f"refused {FIRST}->{LAST}: {type(exc).__name__}")
        return tracer

    return tracer, notes


def run(event):
    ran = []
    tracer, notes = make_tracer(event)
    sys.settrace(tracer)
    try:
        result = target(ran)
    finally:
        sys.settrace(None)
    print(
        f"{event:6s} {','.join(notes) or 'no move'} ran={''.join(ran)} "
        f"B_skipped={'no' if 'B' in ran else 'yes'} result={result}"
    )


for case in sys.argv[1:] or ["line", "opcode"]:
    run(case)
