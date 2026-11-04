"""CPython 3.15 gh-41779: `__slots__` on variable-size bases.

Spec read from Objects/typeobject.c of the 3.15 tree: `type_new_descriptors`
has exactly one rejection - `base->tp_itemsize != 0` and the base is not a
tuple subclass - and its message is "arbitrary __slots__ not supported for
subtype of '<base>'". Everything else, including `__dict__` and `__weakref__`
on any base, is allowed. Before 3.15 a tuple subtype could not declare slots at
all, which is why `Lib/urllib/parse.py` still carries three `TODO: RUSTPYTHON`
lines instead of `__slots__ = ('_keep_empty',)`.

The storage question is what makes this more than a guard change: a RustPython
tuple keeps its elements in a side buffer (`TupleElements`), and instance slots
live in the `ObjExt` prefix in front of `PyInner`, so slot offsets never have to
move past the items - CPython's `_Py_AFTER_ITEMS` arithmetic has no counterpart
here. These tests therefore pin the *observable* result: the slot behaves like
any other slot on an object that is still a working tuple.
"""
import collections
import copy
import gc
import pickle
import unittest
import weakref


class TupleSlotsTest(unittest.TestCase):
    def test_tuple_subtype_accepts_slots(self):
        class T(tuple):
            __slots__ = ("x",)

        t = T((1, 2))
        t.x = 5
        self.assertEqual(t.x, 5)
        self.assertEqual(tuple(t), (1, 2))

    def test_slot_read_before_write_raises(self):
        class T(tuple):
            __slots__ = ("x",)

        with self.assertRaises(AttributeError):
            T(()).x

    def test_no_instance_dict_with_slots(self):
        class T(tuple):
            __slots__ = ("x",)

        t = T((1,))
        with self.assertRaises(AttributeError):
            t.__dict__
        with self.assertRaises(AttributeError):
            t.other = 1

    def test_namedtuple_subtype_accepts_slots(self):
        Point = collections.namedtuple("Point", "a b")

        class P(Point):
            __slots__ = ("z",)

        p = P(1, 2)
        p.z = 3
        self.assertEqual((p.a, p.b, p.z), (1, 2, 3))
        self.assertEqual(p._asdict(), {"a": 1, "b": 2})

    def test_dict_and_weakref_slots_on_tuple_subtype(self):
        # The other gh-41779 bullet: `__dict__`/`__weakref__` stay legal.
        class T(tuple):
            __slots__ = ("__dict__",)

        t = T((1,))
        t.anything = 2
        self.assertEqual(t.anything, 2)
        self.assertEqual(t.__dict__, {"anything": 2})

        class W(tuple):
            __slots__ = ("__weakref__",)

        w = W((1,))
        ref = weakref.ref(w)
        self.assertIs(ref(), w)
        with self.assertRaises(AttributeError):
            w.anything = 1

    def test_slot_tuple_survives_copy_and_gc(self):
        class T(tuple):
            __slots__ = ("x",)

        t = T((1, 2))
        t.x = [3]
        self.assertIsNot(copy.copy(t), t)
        self.assertEqual(copy.copy(t).x, [3])
        del t
        gc.collect()

    def test_variable_size_non_tuple_base_still_rejected(self):
        # int keeps tp_itemsize == sizeof(digit) in 3.15, so it stays refused;
        # the message is the 3.15 wording, not the pre-3.15 one.
        with self.assertRaises(TypeError) as ctx:
            class I(int):
                __slots__ = ("x",)
        self.assertIn("__slots__", str(ctx.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
