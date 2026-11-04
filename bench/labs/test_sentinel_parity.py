"""CPython 3.15 `sentinel` (PEP 661, gh-148829) behavioral parity.

Transcribed from Lib/test/test_builtin.py of the 3.15 tree (test_sentinel,
test_sentinel_attributes, test_sentinel_repr, test_sentinel_pickle,
test_sentinel_str_subclass_name_cycle, test_sentinel_union) plus the
implementation in Objects/sentinelobject.c, so every expectation here is the
reference behaviour rather than something this fork happens to do:

  sentinel(name, /, *, repr=None) -> unique object
    * name positional-only and str (subclasses kept by identity), repr str|None
    * type is immutable and NOT a base type - subclassing is refused
    * __name__ read-only member, __module__ writable and deletable member
    * repr() is the custom repr else the name; copy/deepcopy keep identity
    * __reduce__ returns the name, so pickle resolves (or rejects) by module global
    * identity equality, identity hash, truthy, gc-tracked
    * `|` builds type expressions, collapses a single member, and rejects
      non-unionable operands on both sides

On CPython 3.14 this file cannot even import (no sentinel builtin), which is
why the expected-green reference here is the 3.15 source, not a local binary.
"""
import copy
import gc
import pickle
import unittest
import weakref
from builtins import sentinel

BY_NAME = sentinel("BY_NAME")


class SentinelContainer:
    CLASS_SENTINEL = sentinel("SentinelContainer.CLASS_SENTINEL")


class SentinelTest(unittest.TestCase):
    def test_sentinel(self):
        missing = sentinel("MISSING")
        other = sentinel("MISSING")

        self.assertIsInstance(missing, sentinel)
        self.assertIs(type(missing), sentinel)
        self.assertEqual(missing.__name__, "MISSING")
        self.assertEqual(missing.__module__, __name__)
        self.assertIsNot(missing, other)
        self.assertEqual(repr(missing), "MISSING")
        self.assertTrue(missing)
        self.assertIs(copy.copy(missing), missing)
        self.assertIs(copy.deepcopy(missing), missing)
        self.assertEqual(missing, missing)
        self.assertNotEqual(missing, other)

    def test_argument_binding(self):
        self.assertRaises(TypeError, sentinel)
        self.assertRaises(TypeError, sentinel, "MISSING", "EXTRA")
        self.assertRaises(TypeError, sentinel, name="MISSING")
        with self.assertRaisesRegex(TypeError, "must be str"):
            sentinel(1)

    def test_type_is_not_a_base_type(self):
        # The numeric __flags__ cannot be compared: RustPython's PyTypeFlags is
        # its own bit layout (object is 0x500 here vs CPython 0x1502), so only
        # the behaviour is pinned - which is what CPython's own test checks
        # through these same three bits.
        with self.assertRaises(TypeError):
            class SubSentinel(sentinel):
                pass

    def test_sentinel_attributes(self):
        missing = sentinel("MISSING")
        with self.assertRaises(TypeError):
            sentinel.attribute = "value"
        with self.assertRaises(AttributeError):
            missing.attribute = "value"
        with self.assertRaises(AttributeError):
            missing.__name__ = "CHANGED"
        missing.__module__ = "changed"
        self.assertEqual(missing.__module__, "changed")
        with self.assertRaises(AttributeError):
            del missing.__name__
        del missing.__module__
        with self.assertRaises(AttributeError):
            missing.__module__

    def test_sentinel_repr(self):
        with_repr = sentinel("WITH_REPR", repr="custom")
        without_repr = sentinel("WITHOUT_REPR", repr=None)
        self.assertEqual(repr(with_repr), "custom")
        self.assertEqual(repr(without_repr), "WITHOUT_REPR")
        self.assertEqual(str(with_repr), "custom")
        self.assertEqual(str(without_repr), "WITHOUT_REPR")

        with self.assertRaisesRegex(TypeError, "repr.*str or None"):
            sentinel("BAD_REPR", repr=42)

    def test_sentinel_pickle(self):
        for proto in range(pickle.HIGHEST_PROTOCOL + 1):
            with self.subTest(protocol=proto):
                self.assertIs(
                    pickle.loads(pickle.dumps(BY_NAME, protocol=proto)),
                    BY_NAME)
                self.assertIs(
                    pickle.loads(pickle.dumps(
                        SentinelContainer.CLASS_SENTINEL, protocol=proto)),
                    SentinelContainer.CLASS_SENTINEL)

        missing = sentinel("MISSING")
        for proto in range(pickle.HIGHEST_PROTOCOL + 1):
            with self.subTest(protocol=proto):
                with self.assertRaises(pickle.PicklingError):
                    pickle.dumps(missing, protocol=proto)

    def test_sentinel_str_subclass_name_cycle(self):
        class Name(str):
            pass

        name = Name("MISSING")
        missing = sentinel(name)
        self.assertIs(missing.__name__, name)
        self.assertTrue(gc.is_tracked(missing))

        name.missing = missing
        ref = weakref.ref(name)
        del name, missing
        gc.collect()
        self.assertIsNone(ref())

    def test_sentinel_union(self):
        missing = sentinel("MISSING")

        self.assertEqual((missing | int).__args__, (missing, int))
        self.assertEqual((int | missing).__args__, (int, missing))
        self.assertIs(missing | missing, missing)
        self.assertEqual(repr(int | missing), "int | MISSING")
        self.assertEqual((missing | None).__args__, (missing, type(None)))
        self.assertEqual((None | missing).__args__, (type(None), missing))
        self.assertEqual((missing | list[int]).__args__, (missing, list[int]))
        self.assertEqual((missing | (int | str)).__args__, (missing, int, str))

        with self.assertRaises(TypeError):
            missing | 1
        with self.assertRaises(TypeError):
            1 | missing

    def test_hash_and_dict_lookup(self):
        s = sentinel("H")
        d = {s: 1}
        self.assertEqual(d[s], 1)
        self.assertNotIn(sentinel("H"), d)


if __name__ == "__main__":
    unittest.main(verbosity=2)
