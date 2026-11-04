"""Pin the observable behavior of the dispatch arms moved out of execute_instruction.

The refactor in `crates/vm/src/frame.rs` (task #64) only changes where an arm's
body lives, so the test that proves it is "every shape answers the same way".
Each case below is the Python shape that reaches one extracted arm, run enough
times to reach the specialized form, and the whole file prints a line per case
so a run before and after the move can be diffed byte for byte. Run it on
CPython too: a shape that differs there is a parity bug, not a refactor bug.

    python bench/labs/test_cold_arms.py
"""

import sys

WARM = 60


def note(name, value):
    print(f"{name:28s} {value!r}")


def match_class():
    class Point:
        def __init__(self, x, y):
            self.x, self.y = x, y

    out = []
    for i in range(WARM):
        p = Point(i, i * 2)
        match p:
            case Point(x=int() as x, y=y) if x < 3:
                out.append(("guard", x, y))
            case Point(x=0, y=0):
                out.append("origin")
            case Point():
                out.append((p.x, p.y))
            case _:
                out.append("nope")
    return out[:3], out[-1], len(out)


def match_keys():
    out = []
    for i in range(WARM):
        d = {"a": i, "b": i + 1}
        match d:
            case {"a": first, **rest}:
                out.append((first, tuple(sorted(rest))))
            case _:
                out.append("nope")
    return out[0], out[-1]


def dict_merge():
    total = {}
    for i in range(WARM):
        merged = {**{"k": i}, **{"j": i}, "extra": 1}
        total[i % 2] = merged
    return total[0], total[1]


def yield_from():
    def inner():
        got = yield
        while got is not None:
            yield got * 2
            got = yield

    def outer():
        return (yield from inner())

    gen = outer()
    next(gen)
    seen = [gen.send(v) for v in (1, 2, 3, None)]
    return seen


def super_shapes():
    class Base:
        attr = "base-attr"

        def method(self, n=0):
            return ("base", n)

    class Sub(Base):
        attr = "sub-attr"

        def method(self, n=0):
            return ("sub", n, super().method(n))

    acc = []
    for i in range(WARM):
        s = Sub()
        acc.append((super(Sub, s).attr, s.method(i)[2]))
        acc.append((s.attr, s.method()["2" if False else 2]))
    return acc[0], acc[-1], len(acc)


def except_match():
    hits = []
    for i in range(WARM):
        try:
            if i % 3 == 0:
                raise ValueError("v")
            raise KeyError("k")
        except (IndexError, KeyError) as exc:
            hits.append(("tuple", type(exc).__name__))
        except ValueError as exc:
            hits.append(("single", str(exc)))
    return hits[0], hits[1], len(hits)


def method_descriptors():
    acc = []
    for _ in range(WARM):
        acc.append(int.__add__(1, 2))
        acc.append(str.upper("ab"))
        lst = []
        list.append(lst, 7)
        acc.append(lst)
        acc.append(dict.get({"a": 1}, "a", default=2))
    return acc[0], acc[-1], len(acc)


def type_with_init():
    class Ctor:
        def __init__(self, a, b=2):
            self.a, self.b = a, a + b

    made = [Ctor(i) for i in range(WARM)]
    return (made[0].a, made[0].b, made[-1].a, made[-1].b)


def non_py_general():
    args = (1, 2, 3)
    out = []
    for i in range(WARM):
        out.append(max(*args, i))
        out.append(" ".join(str(x) for x in (i, i + 1)))
    return out[0], out[-1]


def keyword_calls():
    def plain(a, b=None, *, c=0):
        return (a, b, c)

    class Holder:
        def meth(self, a, b=None, *, c=0):
            return (self, a, b, c)[:3]

    h = Holder()
    acc = []
    for i in range(WARM):
        acc.append(plain(i, b=i + 1, c=i + 2))
        acc.append(h.meth(i, c=i))
    return acc[0], acc[-1], len(acc)


def main():
    for name, fn in (
        ("MatchClass", match_class),
        ("MatchKeys", match_keys),
        ("DictMerge", dict_merge),
        ("SendGen", yield_from),
        ("LoadSuperAttr", super_shapes),
        ("CheckExcMatch", except_match),
        ("CallMethodDescriptor", method_descriptors),
        ("CallAllocAndEnterInit", type_with_init),
        ("CallNonPyGeneral", non_py_general),
        ("CallKw", keyword_calls),
    ):
        try:
            note(name, fn())
        except Exception as exc:  # noqa: BLE001 - a refactor must not change this either
            note(name, f"RAISED {type(exc).__name__}: {exc}")
    note("version", (sys.version_info[:3], sys.implementation.name))


main()
