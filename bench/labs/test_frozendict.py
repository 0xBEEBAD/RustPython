"""Parity test for the PEP 814 builtin ``frozendict``.

The test is intended for CPython 3.15+ and RustPython builds that provide the
builtin.  CPython 3.14 does not have ``frozendict``, so it is not run there.

Exit status is 0 only when every check passes and prints ``RESULT OK``.
"""

import collections.abc
import copy
import pickle
import sys

PASS = []
FAIL = []


def check(name, fn):
    try:
        fn()
    except Exception as exc:  # noqa: BLE001
        FAIL.append((name, exc))
        print(f"FAIL {name}: {type(exc).__name__}: {exc}")
        import traceback

        traceback.print_exc()
    else:
        PASS.append(name)
        print(f"PASS {name}")


class FrozenDict(frozendict):
    pass


class FrozenDictSlots(frozendict):
    __slots__ = ("slot_attr",)


def t_construction():
    assert frozendict() == {}
    assert frozendict({"a": 1}) == {"a": 1}
    assert frozendict([("a", 1), ("b", 2)]) == {"a": 1, "b": 2}
    assert frozendict(a=1, b=2) == {"a": 1, "b": 2}
    assert frozendict({"a": 1}, b=2) == {"a": 1, "b": 2}


def t_identity_shortcut():
    fd = frozendict(x=1, y=2)
    assert frozendict(fd) is fd
    sub = FrozenDict(fd)
    assert sub is not fd
    assert sub == fd
    assert type(sub) is FrozenDict


def t_init_noop_and_dict_init():
    d = frozendict(a=1, b=2, c=3)
    d.__init__(x=1)
    assert d == frozendict(a=1, b=2, c=3)
    try:
        dict.__init__(d, x=1)
    except TypeError:
        pass
    else:
        raise AssertionError("dict.__init__(frozendict) must raise TypeError")


def t_immutable():
    fd = frozendict(a=1)
    for name in ("update", "pop", "popitem", "setdefault", "clear", "__setitem__"):
        assert not hasattr(fd, name), name
    for fn in (
        lambda: fd.__setitem__("b", 2),
        lambda: fd.__delitem__("a"),
        lambda: fd.update({"b": 2}),
        lambda: fd.pop("a"),
        lambda: fd.clear(),
    ):
        try:
            fn()
        except (AttributeError, TypeError):
            pass
        else:
            raise AssertionError("mutation unexpectedly succeeded")
    try:
        fd["b"] = 2
    except TypeError:
        pass
    else:
        raise AssertionError("item assignment must raise TypeError")


def t_read_ops():
    fd = frozendict(a=1, b=2, c=3)
    assert len(fd) == 3
    assert fd["a"] == 1
    assert fd.get("a") == 1
    assert fd.get("zzz") is None
    assert fd.get("zzz", 9) == 9
    assert "a" in fd and "zzz" not in fd
    assert set(fd) == {"a", "b", "c"}
    assert set(fd.keys()) == {"a", "b", "c"}
    assert set(fd.values()) == {1, 2, 3}
    assert set(fd.items()) == {("a", 1), ("b", 2), ("c", 3)}
    assert list(reversed(fd)) == list(reversed(list(fd)))
    try:
        fd["zzz"]
    except KeyError:
        pass
    else:
        raise AssertionError("missing key must raise KeyError")


def t_equality():
    fd = frozendict(a=1, b=2)
    assert fd == {"a": 1, "b": 2}
    assert {"a": 1, "b": 2} == fd
    assert fd == frozendict(b=2, a=1)
    assert fd == FrozenDict(a=1, b=2)
    assert fd != {"a": 1}
    assert fd != {"a": 1, "b": 3}
    assert fd != [("a", 1), ("b", 2)]


def t_mapping_abc():
    assert isinstance(frozendict(), collections.abc.Mapping)
    assert isinstance(FrozenDict(), collections.abc.Mapping)


def t_hash():
    assert hash(frozendict(x=1, y=2)) == hash(frozendict(y=2, x=1))
    assert hash(frozendict(x=1)) == hash(FrozenDict(x=1))
    for fd in (
        frozendict(),
        frozendict(x=1, y=2),
        frozendict(a=False, b=True, c=True),
        frozendict.fromkeys("abc"),
    ):
        assert hash(fd) == hash(frozenset(fd.items())), fd
    cases = [
        frozendict(a=False, b=True, c=True),
        frozendict(a=True, b=False, c=True),
        frozendict(a=True, b=True, c=False),
        frozendict({False: "a", "b": True, "c": True}),
        frozendict({"a": "b", False: True, True: "c"}),
    ]
    assert len({hash(fd) for fd in cases}) == len(cases)
    try:
        hash(frozendict(x=[1]))
    except TypeError as exc:
        assert "unhashable type: 'list'" in str(exc), exc
    else:
        raise AssertionError("hash of list value must raise TypeError")


def t_unhashable_lookup():
    fd = frozendict(a=1)
    key = [1, 2, 3]
    expected = "cannot use 'list' as a frozendict key (unhashable type: 'list')"
    for fn in (lambda: key in fd, lambda: fd[key], lambda: fd.get(key)):
        try:
            fn()
        except TypeError as exc:
            assert str(exc) == expected, str(exc)
        else:
            raise AssertionError("unhashable lookup must raise TypeError")


def t_repr():
    assert repr(frozendict()) == "frozendict()"
    assert repr(frozendict(x=1, y=2)) == "frozendict({'x': 1, 'y': 2})"
    assert repr(FrozenDict(x=1, y=2)) == "FrozenDict({'x': 1, 'y': 2})"


def t_or():
    assert frozendict(x=1) | frozendict(y=2) == frozendict({"x": 1, "y": 2})
    assert frozendict(x=1) | dict(y=2) == frozendict({"x": 1, "y": 2})
    assert frozendict(x=1, y=2) | frozendict(y=5) == frozendict({"x": 1, "y": 5})
    assert FrozenDict(x=1, y=2) | FrozenDict(y=5) == frozendict({"x": 1, "y": 5})
    fd = frozendict(x=1, y=2)
    assert fd | frozendict() is fd
    assert fd | {} is fd
    assert frozendict() | fd is fd
    a = frozendict({"a": 1})
    b = frozendict({"b": 2})
    assert hash(a | b) == hash(frozendict({"a": 1, "b": 2}))


def t_ior():
    d = frozendict(x=1)
    alias = d
    d |= frozendict(y=2)
    assert alias is not d
    assert alias == frozendict(x=1)
    assert d == frozendict({"x": 1, "y": 2})


def t_items_xor():
    res = frozendict(a=1, b=2).items() ^ frozendict(b=2, c=3).items()
    assert res == {("a", 1), ("c", 3)}


def t_fromkeys():
    assert frozendict.fromkeys("abc") == frozendict(a=None, b=None, c=None)
    fd = FrozenDictSlots.fromkeys("ab", 0)
    assert fd == frozendict(a=0, b=0)
    assert type(fd) is FrozenDictSlots


def t_copy():
    fd = frozendict(x=1, y=2)
    assert fd.copy() is fd
    sub = FrozenDict(x=1, y=2)
    sub_copy = sub.copy()
    assert sub_copy is not sub
    assert sub_copy == fd
    assert type(sub_copy) is frozendict
    assert copy.copy(fd) == fd
    assert copy.deepcopy(fd) == fd


def t_pickle():
    for proto in range(2, pickle.HIGHEST_PROTOCOL + 1):
        for fd in (frozendict(), frozendict(x=1, y=2), FrozenDict(x=1, y=2)):
            if type(fd) is FrozenDict:
                fd.attr = 123
            out = pickle.loads(pickle.dumps(fd, proto))
            assert out == fd
            assert type(out) is type(fd)
            if type(fd) is FrozenDict:
                assert out.attr == 123

        slots = FrozenDictSlots(x=1, y=2)
        slots.slot_attr = 456
        out = pickle.loads(pickle.dumps(slots, proto))
        assert out == slots
        assert type(out) is FrozenDictSlots
        assert out.slot_attr == 456

    for proto in (0, 1):
        try:
            pickle.dumps(frozendict(x=1), proto)
        except TypeError:
            pass
        else:
            raise AssertionError(f"pickle protocol {proto} must raise TypeError")


def t_slots_subclass():
    fd = FrozenDictSlots(a=1)
    fd.slot_attr = 7
    assert fd.slot_attr == 7
    assert fd == frozendict(a=1)
    try:
        fd.other = 1
    except AttributeError:
        pass
    else:
        raise AssertionError("__slots__ subclass must reject other attributes")

    plain = FrozenDict(a=1)
    plain.attr = 123
    assert plain.attr == 123


def t_unpacking():
    fd = frozendict(a=1, b=2)

    def f(**kwargs):
        return kwargs

    assert f(**fd) == {"a": 1, "b": 2}
    assert dict(**fd) == {"a": 1, "b": 2}
    assert {**fd, "c": 3} == {"a": 1, "b": 2, "c": 3}


def t_name():
    assert frozendict.__name__ == "frozendict"
    assert frozendict.__qualname__ == "frozendict"
    assert sys.modules["builtins"].frozendict is frozendict


def main():
    tests = [
        ("construction", t_construction),
        ("identity_shortcut", t_identity_shortcut),
        ("init_noop_and_dict_init", t_init_noop_and_dict_init),
        ("immutable", t_immutable),
        ("read_ops", t_read_ops),
        ("equality", t_equality),
        ("mapping_abc", t_mapping_abc),
        ("hash", t_hash),
        ("unhashable_lookup", t_unhashable_lookup),
        ("repr", t_repr),
        ("or", t_or),
        ("ior", t_ior),
        ("items_xor", t_items_xor),
        ("fromkeys", t_fromkeys),
        ("copy", t_copy),
        ("pickle", t_pickle),
        ("slots_subclass", t_slots_subclass),
        ("unpacking", t_unpacking),
        ("name", t_name),
    ]
    for name, fn in tests:
        check(name, fn)

    print(f"PASSED {len(PASS)}, FAILED {len(FAIL)}")
    if FAIL:
        return 1
    print("RESULT OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
