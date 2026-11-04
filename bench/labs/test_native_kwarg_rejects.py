"""Natives that swallow a keyword argument CPython rejects.

A hand-written `__new__` that consumes only the positional half of its `FuncArgs`
answers `chain(zzzq=1)` by building the object; CPython answers
`chain() takes no keyword arguments`. `bench/labs/kwarg_acceptors.py` finds such
callables across the stdlib - this is the pinned behaviour of the ones still open,
plus the positive cases that must not break and the type names that show up in
the messages.

    python bench/labs/test_native_kwarg_rejects.py
"""

import collections
import gc
import itertools
import types


def check(label, fn, expect):
    try:
        got = fn()
    except BaseException as exc:
        got = f"{type(exc).__name__}: {exc}"
    else:
        got = repr(got)
    print(f"{'ok  ' if got == expect else 'FAIL'} {label:42s} {got}")
    return got == expect


results = [
    # itertools.chain: a type with a hand-written slot_new.
    check("chain(zzzq=1)", lambda: itertools.chain(zzzq=1),
          "TypeError: chain() takes no keyword arguments"),
    check("chain(1, 2, x=1)", lambda: itertools.chain(1, 2, x=1),
          "TypeError: chain() takes no keyword arguments"),
    check("_chain(zzzq=1)", lambda: collections._chain(zzzq=1),
          "TypeError: chain() takes no keyword arguments"),
    check("chain.from_iterable(zzzq=1)", lambda: itertools.chain.from_iterable(zzzq=1),
          "TypeError: chain.from_iterable() takes no keyword arguments"),
    # Positives: the accepted shapes have to stay accepted.
    check("chain([]) length", lambda: len(list(itertools.chain([]))), "0"),
    check("chain('ab')", lambda: list(itertools.chain("ab")), "['a', 'b']"),
    check("chain.from_iterable([[1],[2]])",
          lambda: list(itertools.chain.from_iterable([[1], [2]])), "[1, 2]"),
    check("chain(1, 2) iterates", lambda: list(itertools.chain(1, 2)),
          "TypeError: 'int' object is not iterable"),
    check("_chain is chain", lambda: collections._chain is itertools.chain, "True"),
    # gc: positional-only varargs natives.
    check("gc.get_referents(zzzq=1)", lambda: gc.get_referents(zzzq=1),
          "TypeError: gc.get_referents() takes no keyword arguments"),
    check("gc.get_referrers(zzzq=1)", lambda: gc.get_referrers(zzzq=1),
          "TypeError: gc.get_referrers() takes no keyword arguments"),
    check("gc.get_referents(zzzq=1, yyyq=2)", lambda: gc.get_referents(zzzq=1, yyyq=2),
          "TypeError: gc.get_referents() takes no keyword arguments"),
    check("gc.get_referents()", lambda: gc.get_referents(), "[]"),
    check("gc.get_referents([])", lambda: len(gc.get_referents([])) >= 0, "True"),
    check("gc.get_referrers([])", lambda: isinstance(gc.get_referrers([]), list), "True"),
    check("gc.collect(zzzq=1)", lambda: gc.collect(zzzq=1),
          "TypeError: collect() got an unexpected keyword argument 'zzzq'"),
]

# Open gaps, printed but not counted: both need a rule this unit does not add.
# `gc.set_threshold`'s CPython name is the bare `set_threshold` (that is its
# `ml_name`), while the qualified-name helper synthesizes `gc.set_threshold`;
# fixing it means declaring real method-table names per module, not per call site.
# `classmethod_descriptor` does not exist as a type here at all - C-implemented
# classmethods are `method_descriptor` objects, so `types.ClassMethodDescriptorType`
# is an alias rather than the distinct class CPython has.
gaps = [
    check("gap: gc.set_threshold(zzzq=1)", lambda: gc.set_threshold(zzzq=1),
          "TypeError: set_threshold() takes no keyword arguments"),
    check("gap: ClassMethodDescriptorType name",
          lambda: types.ClassMethodDescriptorType.__name__, "'classmethod_descriptor'"),
    check("gap: dict.fromkeys class name",
          lambda: type(dict.__dict__["fromkeys"]).__name__, "'classmethod_descriptor'"),
]

print(f"passed {sum(results)}/{len(results)}  (open gaps: {sum(gaps)}/{len(gaps)})")
