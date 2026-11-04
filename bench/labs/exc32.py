"""What is the extra 32-byte block every exception construction pays?

`ValueError()` costs two blocks (32 + 176) while the 176 is the object itself, so
something beside the object is allocated per exception. This runs the same window
over controls that build comparable objects - `object()`, a user class, `list()`,
`dict()`, `str()` - and over exception variants, so the block can be attributed by
which shapes share it.

    target/allocstats/release/rustpython.exe bench/labs/exc32.py [n]
"""

import sys

N = int(sys.argv[1]) if len(sys.argv) > 1 else 50_000
import itertools
repeat = itertools.repeat


def stats(reset=True):
    value = sys._alloc_stats(reset)
    if isinstance(value, dict):
        return value["allocs"], value["frees"], value["sizes"]
    return value


def window(label, fn):
    stats(True)
    fn(N)
    allocs, frees, sizes = stats(False)
    per = [f"{size}:{count / N:.3f}" for size, count in sorted(sizes) if count / N > 0.05]
    print(f"{label:24s} allocs/op={allocs / N:.3f} frees/op={frees / N:.3f}  {per}")


class Plain:
    pass


class WithDict:
    def __init__(self):
        self.x = 1


def object_new(n):
    for _ in repeat(None, n):
        object()


def plain_new(n):
    c = Plain
    for _ in repeat(None, n):
        c()


def with_dict_new(n):
    c = WithDict
    for _ in repeat(None, n):
        c()


def list_new(n):
    for _ in repeat(None, n):
        list()


def dict_new(n):
    for _ in repeat(None, n):
        dict()


def str_new(n):
    for _ in repeat(None, n):
        str()


def ve_new(n):
    c = ValueError
    for _ in repeat(None, n):
        c()


def ve_arg(n):
    c = ValueError
    for _ in repeat(None, n):
        c("x")


def base_exc(n):
    c = BaseException
    for _ in repeat(None, n):
        c()


def exc_new_only(n):
    new = ValueError.__new__
    for _ in repeat(None, n):
        new(ValueError)


def exc_dict_read(n):
    c = ValueError
    for _ in repeat(None, n):
        e = c()
        e.__dict__


def exc_str(n):
    c = ValueError
    for _ in repeat(None, n):
        str(c("x"))


print(f"== {sys.implementation.name} ==")
for name, fn in (
    ("object()", object_new),
    ("Plain()", plain_new),
    ("WithDict()", with_dict_new),
    ("list()", list_new),
    ("dict()", dict_new),
    ("str()", str_new),
    ("ValueError()", ve_new),
    ("ValueError('x')", ve_arg),
    ("BaseException()", base_exc),
    ("__new__(ValueError)", exc_new_only),
    ("VE(); e.__dict__", exc_dict_read),
    ("str(Ve('x'))", exc_str),
):
    window(name, fn)
for name, fn in (
    ("TypeError()", lambda n: [TypeError() for _ in range(0)] or None),
):
    pass
