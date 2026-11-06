"""Only a real struct sequence may be sliced by `n_sequence_fields`.

Fixing struct_time's `+` needed a way to ask "is this operand a struct
sequence?" from inside `PyTuple::__add__`. The cheap answer - "does its class
have an integer `n_sequence_fields`?" - is also true of any user tuple subclass
that happens to define that attribute, and CPython does NOT treat such a class
specially: for CPython the visible length is `Py_SIZE`, which only
`PyStructSequence_NewType` ever makes smaller than the body. So this probe pins
what a plain tuple subclass with struct-sequence-shaped attributes must do.

    bench/labs/cp314/python.exe                    bench/labs/test_tuple_seq_attr.py
    target/release/rustpython.exe                  bench/labs/test_tuple_seq_attr.py
"""

import time


class Lookalike(tuple):
    n_sequence_fields = 2
    n_fields = 2
    n_unnamed_fields = 0


class ShorterThanItLooks(tuple):
    n_sequence_fields = 2
    n_fields = 9  # deliberately not the body length


failures = []


def raises_index(seq):
    try:
        _type, (shown, hidden) = seq.__reduce__()
        seq.index(next(iter(hidden.values())))
    except ValueError:
        return "ValueError"
    return "no raise"


def check(label, got, want):
    if got != want:
        failures.append(label)
    print(f"{'ok  ' if got == want else 'FAIL'} {label:34s} got {got!r} want {want!r}")


look = Lookalike((10, 20, 30, 40))
short = ShorterThanItLooks((1, 2, 3))

# a user-defined subclass is a plain tuple in CPython: every item counts
check("lookalike + tuple", look + (99,), (10, 20, 30, 40, 99))
check("tuple + lookalike", (99,) + look, (99, 10, 20, 30, 40))
check("lookalike len", len(look), 4)
check("lookalike count", look.count(30), 1)
check("lookalike index", look.index(30), 2)
check("lookalike * 2", look * 2, (10, 20, 30, 40, 10, 20, 30, 40))
check("n_fields mismatch", short + (9,), (1, 2, 3, 9))

# and a real struct sequence must still be sliced the other way
t = time.localtime(0)
n_seq = t.n_sequence_fields
check("struct_time body is longer than it shows", t.n_fields > n_seq, True)
check("struct_time + tuple", len(t + (9,)), n_seq + 1)
check("tuple + struct_time", len((9,) + t), n_seq + 1)
check("struct_time index of a hidden field", raises_index(t), "ValueError")

print(f"{len(failures)} failures")
