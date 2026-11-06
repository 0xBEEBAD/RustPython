"""Struct sequences must show only their visible fields to every operator.

CPython gives a structseq object `ob_size` == `n_sequence_fields` and parks the
hidden fields in the type's extra `tp_basicsize` (Objects/structseq.c:
`#define VISIBLE_SIZE(op) Py_SIZE(op)`), so the inherited tuple slots are
correct without knowing anything about struct sequences. We keep the whole
`n_fields` body inside a real PyTuple and slice by hand, so every slot that
touches the body has to be cut down -- including `nb_add`, which tuple only
gained recently and which therefore shadows our `sq_concat` override.

Run this against the reference interpreter first: a row that passes on CPython
is what makes the expectation evidence rather than a restatement of our code.
    bench/labs/cp314/python.exe bench/labs/test_structseq_visible.py
    target/release/rustpython.exe bench/labs/test_structseq_visible.py
"""

import os
import sys
import time
import socket


def visible(t):
    return tuple(t)[: t.n_sequence_fields]


ROWS = []


class Reflected:
    """Only reachable if the left operand declines the addition."""

    def __radd__(self, other):
        return ("radd", len(other))



def check(name, got, want):
    ROWS.append((name, repr(got), repr(want), got == want))


def probe(seq, label):
    """Every body-touching operation on one struct sequence instance."""
    n_seq = seq.n_sequence_fields
    n_all = seq.n_fields
    tail = (100, 101)
    hidden = hidden_value(seq, n_seq, n_all)

    check(f"{label}.len", len(seq), n_seq)
    check(f"{label}+tuple.len", len(seq + tail), n_seq + len(tail))
    check(f"{label}+empty.len", len(seq + ()), n_seq)
    check(f"{label}+tuple.value", seq + tail, visible(seq) + tail)
    check(f"{label}+tuple[9]", seq + tail, visible(seq) + tail)
    check(f"{label}+seq.len", len(seq + type(seq)(visible(seq))), 2 * n_seq)
    # The struct sequence on the *right* is read by the left operand's own
    # slot, so no override on the structseq type can reach it.
    check(f"{label}as-rhs.len", len(tail + seq), len(tail) + n_seq)
    check(f"{label}as-rhs.value", tail + seq, tail + visible(seq))
    check(f"{label}as-rhs.self", len(visible(seq) + seq), 2 * n_seq)
    check(f"{label}+tuple.__add__", seq.__add__(tail), visible(seq) + tail)
    check(f"{label}+reflected", seq + Reflected(), ("radd", len(seq)))
    check(f"{label}*2.len", len(seq * 2), 2 * n_seq)
    check(f"{label}*2.value", seq * 2, visible(seq) + visible(seq))
    check(f"{label}.rmul", 2 * seq, visible(seq) + visible(seq))
    check(f"{label}.getitem", seq[n_seq - 1], visible(seq)[-1])
    check(f"{label}.getitem.oob", raises(lambda: seq[n_seq], IndexError), True)
    check(f"{label}.iter", list(seq), list(visible(seq)))
    check(f"{label}.slice", seq[1:n_seq], visible(seq)[1:])
    check(f"{label}.hash", hash(seq), hash(visible(seq)))
    check(f"{label}.eq", seq == visible(seq), True)
    check(f"{label}.contains.hidden", hidden is None or hidden not in seq, True)
    check(f"{label}.contains-method", hidden is None or not seq.__contains__(hidden), True)
    check(f"{label}.count.hidden", seq.count(hidden), 0)
    check(f"{label}.index.hidden", raises(lambda: seq.index(hidden), ValueError), True)
    check(f"{label}.count.of-visible", seq.count(visible(seq)[-1]), visible(seq).count(visible(seq)[-1]))
    check(f"{label}.index.of-visible", seq.index(visible(seq)[-1]), visible(seq).index(visible(seq)[-1]))
    check(f"{label}.index.ranged", raises(lambda: seq.index(hidden, 0, n_seq), ValueError), True)
    check(f"{label}.reversed", list(reversed(seq)), list(visible(seq))[::-1])
    check(f"{label}.repr.nfields", repr(seq).count("="), n_seq)
    check(f"{label}.bool", bool(seq), True)


def hidden_value(seq, n_seq, n_all):
    """A value that sits in the body past `n_sequence_fields`, or None.

    `__reduce__` is the one place CPython itself admits the real size, so it is
    how this probe reaches a field every other operation must hide.
    """
    try:
        items = seq.__reduce__()[1]
    except Exception:
        return None
    for i in range(n_seq, n_all):
        if isinstance(items, (tuple, list)) and len(items) > i:
            return items[i]
    return None


def raises(fn, exc):
    try:
        fn()
    except exc:
        return True
    except Exception:
        return False
    return False


st = time.localtime(0)
probe(st, "struct_time")

try:
    ts = os.terminal_size((80, 24))
    probe(ts, "terminal_size")
except AttributeError:
    pass

try:
    gi = socket.getaddrinfo("localhost", 80, type=socket.SOCK_STREAM)[0][4]
    n_seq = gi.n_sequence_fields
    check("sockaddr.len", len(gi), n_seq)
    check("sockaddr+tuple.len", len(gi + (9,)), n_seq + 1)
    check("sockaddr+tuple.value", gi + (9,), tuple(gi)[:n_seq] + (9,))
except AttributeError:
    pass

bad = [r for r in ROWS if not r[3]]
for name, got, want, ok in ROWS:
    if not ok:
        print(f"FAIL {name}: got {got} want {want}")
print(f"{len(ROWS) - len(bad)}/{len(ROWS)} rows match CPython")
sys.exit(1 if bad else 0)
