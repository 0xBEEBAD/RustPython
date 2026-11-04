"""Pin CPython 3.15's `bytearray.take_bytes()` for this fork.

CPython 3.15 added `take_bytes(n=None)` (Objects/bytearrayobject.c,
`bytearray_take_bytes_impl`): it removes the first *n* bytes and returns them,
negative *n* counting from the end, `None` meaning all of them. It is the API the
3.15 library uses in `asyncio.streams`, `_pyio`, `wave`, `re._compiler`,
`encodings.idna` and `encodings.punycode`, which this fork currently works
around with `bytes(...)`.

Rows follow CPython's own `test_bytes.test_take_bytes*`, except that this fork's
`__alloc__()` reports the buffer capacity without the object header (its
test_bytes.py is already patched for that), and the MemoryError-atomicity test
needs CPython's allocation-failure injection and so is not reproducible here.

    python bench/labs/test_take_bytes.py
"""

import sys
import unittest


class TestTakeBytes(unittest.TestCase):
    def test_take_all(self):
        ba = bytearray(b"ab")
        self.assertEqual(ba.take_bytes(), b"ab")
        self.assertEqual(len(ba), 0)
        self.assertEqual(ba, bytearray(b""))
        self.assertEqual(ba.__alloc__(), 0)
        self.assertEqual(sys.getsizeof(ba), sys.getsizeof(bytearray()))

    def test_take_prefix_and_negative(self):
        ba = bytearray(b"abcdef")
        self.assertEqual(ba.take_bytes(1), b"a")
        self.assertEqual(ba, bytearray(b"bcdef"))
        self.assertEqual(len(ba), 5)
        self.assertEqual(ba.take_bytes(-5), b"")
        self.assertEqual(ba, bytearray(b"bcdef"))
        self.assertEqual(ba.take_bytes(-3), b"bc")
        self.assertEqual(ba, bytearray(b"def"))
        self.assertEqual(ba.take_bytes(3), b"def")
        self.assertEqual(ba, bytearray(b""))

    def test_take_from_empty(self):
        ba = bytearray(b"abcdef")
        ba.take_bytes()
        self.assertEqual(ba.take_bytes(0), b"")
        self.assertEqual(ba.take_bytes(), b"")
        self.assertEqual(ba.take_bytes(None), b"")

    def test_out_of_range(self):
        ba = bytearray()
        self.assertRaises(IndexError, ba.take_bytes, -1)
        ba = bytearray(b"abcdef")
        self.assertRaises(IndexError, ba.take_bytes, 7)

    def test_error_messages(self):
        ba = bytearray()
        with self.assertRaises(TypeError) as cm:
            ba.take_bytes(3.14)
        self.assertEqual(str(cm.exception), "n must be an integer or None")
        with self.assertRaises(IndexError) as cm:
            ba.take_bytes(-1)
        self.assertEqual(str(cm.exception), "can't take -1 bytes outside size 0")
        ba = bytearray(b"abcdef")
        with self.assertRaises(IndexError) as cm:
            ba.take_bytes(7)
        self.assertEqual(str(cm.exception), "can't take 7 bytes outside size 6")

    def test_index_may_resize_the_bytearray(self):
        # CPython re-reads the size after n.__index__(), which may append.
        ba = bytearray(b"ab")

        class Index:
            def __index__(self):
                ba.extend(b"cdef")
                return 3

        self.assertEqual(ba.take_bytes(Index()), b"abc")
        self.assertEqual(ba, bytearray(b"def"))

    def test_exported_buffer_blocks_the_take(self):
        ba = bytearray(b"abc")
        with memoryview(ba) as mv:
            self.assertRaises(BufferError, ba.take_bytes)
        del mv
        self.assertEqual(ba.take_bytes(), b"abc")

    def test_take_after_shrinking_from_front(self):
        ba = bytearray(b"abcde")
        del ba[:2]
        self.assertEqual(ba, bytearray(b"cde"))
        self.assertEqual(ba.take_bytes(), b"cde")

    def test_leaving_one_byte_does_not_alias(self):
        # CPython must not adopt the shared one-byte bytes singleton here.
        ba = bytearray(b"abc")
        self.assertEqual(ba.take_bytes(2), b"ab")
        ba[0] = ord("A")
        self.assertEqual(ba, bytearray(b"A"))

    def test_allocation_shape(self):
        ba = bytearray(b"abcdef" + b"0" * 1000)
        start_alloc = ba.__alloc__()
        self.assertEqual(ba.take_bytes(2), b"ab")
        self.assertEqual(ba.__alloc__(), start_alloc)
        self.assertEqual(ba.take_bytes(2), b"cd")
        self.assertEqual(ba.__alloc__(), start_alloc)
        self.assertEqual(ba.take_bytes(2), b"ef")
        self.assertEqual(ba.__alloc__(), start_alloc)
        self.assertEqual(len(ba), 1000)
        # Taking at least as much as is left releases the old storage, so the
        # buffer ends up sized to what remains.
        self.assertEqual(ba.take_bytes(501), b"0" * 501)
        self.assertEqual(len(ba), 499)
        self.assertEqual(ba.__alloc__(), 499)
        self.assertEqual(ba, bytearray(b"0" * 499))


if __name__ == "__main__":
    unittest.main(verbosity=2)
