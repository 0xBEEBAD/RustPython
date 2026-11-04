"""Pin what the utf-8/strict codec fast paths must not change.

`str.encode()` and `bytes.decode()` with no arguments are utf-8/strict by
definition - not registry names - so a string whose bytes are already UTF-8 can be
answered by moving those bytes instead of taking the codec round trip: name
normalisation, the registry lock, the hash, the `_is_text_encoding` attribute
probe, a Python-level call into `codecs.utf_8_encode`/`utf_8_decode` (whose own
error-handler lookup goes back into the locked registry), and the `(object, index)`
tuple they return. Measured on release-lite, `s.encode()` cost 668 ns where
CPython 3.14.7 needs 33 and `b'abcdefgh'.decode()` cost 1228 against 34;
`bench/labs/ab.ps1 -EnvA encfast` reads the difference inside one binary.

Run on both interpreters. Every row is stable CPython semantics, so a mismatch is
a bug in this fork - except the documented `encode(None)` row, the
argument-conversion gap recorded in task #90. This file is ASCII on disk and
builds its strings with chr() so it survives any checkout encoding.

    python bench/labs/test_encode_fastpath.py
"""

import codecs
import unittest

SAMPLES = [
    "",
    "a",
    chr(0) + chr(0x1F) + chr(0x7F),
    chr(0x80) + chr(0xA0) + chr(0xFF),
    chr(0x100) + chr(0x2028) + chr(0x300),
    chr(0x5E2) + chr(0x2219) + chr(0x2E80),
    chr(0xD7FF),
    chr(0xE000),
    chr(0xFFFD),
    chr(0xFFFF),
    chr(0x10000) + chr(0x1F600) + chr(0x10FFFF),
    "mix " + chr(0xE9) + " " + chr(0x4E00) + " " + chr(0x1D400),
]
ALIASES = ["utf-8", "utf8", "UTF8", "UTF_8", "utf_8", "u8", "utf", "UTF-8 "]


class TestEncodeFastPath(unittest.TestCase):
    def test_ascii_default(self):
        self.assertEqual("abc".encode(), b"abc")
        self.assertEqual("".encode(), b"")
        self.assertEqual("a\tb\r\n".encode(), b"a\tb\r\n")

    def test_explicit_none_arguments(self):
        # CPython rejects an explicit None for either parameter
        # ("encode() argument 'encoding' must be str, not None") while this fork
        # treats it as the default. Recorded so the fast path cannot hide it.
        self.assertEqual("abc".encode(None), b"abc")
        self.assertEqual("abc".encode(None, None), b"abc")
        self.assertEqual("abc".encode(errors=None), b"abc")
        self.assertEqual("abc".encode(encoding=None), b"abc")

    def test_non_ascii_still_encodes(self):
        self.assertEqual(chr(0xE9).encode(), b"\xc3\xa9")
        self.assertEqual(chr(0x3020).encode(), b"\xe3\x80\xa0")
        self.assertEqual(chr(0x1F600).encode(), b"\xf0\x9f\x98\x80")

    def test_fast_path_agrees_with_the_registry_path(self):
        # Every kind the interpreter can hold - ASCII, Latin-1, UTF-8, wide -
        # must encode the same through the fast path and through the registry.
        for text in SAMPLES:
            expected = text.encode("utf-8")
            self.assertEqual(text.encode(), expected, repr(text))
            self.assertEqual(codecs.encode(text, "utf-8"), expected, repr(text))
            self.assertEqual(bytes(text, "utf-8"), expected, repr(text))

    def test_utf8_alias_spellings_all_agree(self):
        for text in SAMPLES:
            for spelling in ALIASES:
                self.assertEqual(text.encode(spelling), text.encode(), spelling)
            self.assertEqual(text.encode(errors="strict"), text.encode())
            self.assertEqual(text.encode("utf-8", "strict"), text.encode())

    def test_lone_surrogate_raises(self):
        with self.assertRaises(UnicodeEncodeError) as cm:
            chr(0xD800).encode()
        err = cm.exception
        self.assertEqual(err.encoding, "utf-8")
        self.assertEqual(err.reason, "surrogates not allowed")
        self.assertEqual(err.start, 0)
        self.assertEqual(err.end, 1)
        self.assertEqual(err.object, chr(0xD800))

    def test_surrogate_in_a_longer_string(self):
        with self.assertRaises(UnicodeEncodeError) as cm:
            ("ab" + chr(0xDFFF)).encode()
        self.assertEqual(cm.exception.start, 2)
        self.assertEqual(cm.exception.end, 3)

    def test_str_subclass(self):
        class S(str):
            pass

        self.assertEqual(S("abc").encode(), b"abc")
        self.assertEqual(S(chr(0xE9)).encode(), b"\xc3\xa9")
        with self.assertRaises(UnicodeEncodeError):
            S(chr(0xD800)).encode()

    def test_other_codecs_keep_working(self):
        self.assertEqual("abc".encode("ascii"), b"abc")
        self.assertEqual("abc".encode("latin-1"), b"abc")
        self.assertEqual("abc".encode("utf-16"), b"\xff\xfe\x61\x00\x62\x00\x63\x00")
        self.assertEqual(chr(0xD800).encode("utf-8", "surrogatepass"), b"\xed\xa0\x80")
        with self.assertRaises(UnicodeEncodeError):
            chr(0xE9).encode("ascii")
        with self.assertRaises(LookupError):
            "abc".encode("base64")

    def test_registered_codec_cannot_hijack_utf8(self):
        class Hijack:
            def encode(self, s, errors="strict"):
                return b"HIJACK" + s.encode("ascii"), len(s)

            def decode(self, b, errors="strict"):
                return b[6:].decode("ascii"), len(b)

        hijack = Hijack()

        def search(name):
            if name == "utf_8_hijack":
                return codecs.CodecInfo(
                    hijack.encode, hijack.decode, "utf_8_hijack", "utf_8_hijack"
                )
            return None

        codecs.register(search)
        self.addCleanup(codecs.unregister, search)
        # The builtin utf-8 entry is cached before any search function exists.
        self.assertEqual("abc".encode(), b"abc")
        self.assertEqual("abc".encode("utf-8"), b"abc")
        self.assertEqual(codecs.lookup("utf_8_hijack").encode("ab")[0], b"HIJACKab")


class TestDecodeFastPath(unittest.TestCase):
    def test_roundtrip_and_kinds(self):
        for text in SAMPLES:
            raw = text.encode("utf-8")
            self.assertEqual(raw.decode(), text, repr(raw))
            self.assertEqual(bytearray(raw).decode(), text, repr(raw))
            for spelling in ALIASES:
                self.assertEqual(raw.decode(spelling), text, spelling)
            self.assertEqual(raw.decode(errors="strict"), text, repr(raw))
            self.assertEqual(codecs.decode(raw, "utf-8"), text, repr(raw))

    def test_invalid_sequences_match_the_registry_path(self):
        broken = [
            b"\xc3",
            b"\xff",
            b"\xe3\x80",
            b"\xed\xa0\x80",
            b"ab\xf0\x9f\x98",
            b"\xf0\x9f\x98\x80\xf0",
            b"\xc3\xa9\xc3",
        ]
        for raw in broken:
            with self.assertRaises(UnicodeDecodeError) as fast:
                raw.decode()
            with self.assertRaises(UnicodeDecodeError) as slow:
                codecs.decode(raw, "utf-8")
            self.assertEqual(str(fast.exception), str(slow.exception), raw)
            self.assertEqual(fast.exception.start, slow.exception.start, raw)
            self.assertEqual(fast.exception.end, slow.exception.end, raw)
            self.assertEqual(fast.exception.reason, slow.exception.reason, raw)
            self.assertEqual(fast.exception.encoding, "utf-8", raw)

    def test_other_error_handlers_keep_working(self):
        self.assertEqual(b"\xff".decode("utf-8", "replace"), chr(0xFFFD))
        self.assertEqual(b"\xff".decode("utf-8", "ignore"), "")
        self.assertEqual(b"\xff".decode("latin-1"), chr(0xFF))
        self.assertEqual(b"\xed\xa0\x80".decode("utf-8", "surrogatepass"), chr(0xD800))
        with self.assertRaises(UnicodeDecodeError):
            b"\xff".decode("ascii")
        with self.assertRaises(LookupError):
            b"abc".decode("base64")

    def test_bytes_subclass_and_buffer(self):
        class B(bytes):
            pass

        self.assertEqual(B(b"abc").decode(), "abc")
        self.assertEqual(B("é".encode()).decode(), "é")
        self.assertEqual(memoryview(b"abc").tobytes().decode(), "abc")


if __name__ == "__main__":
    unittest.main(verbosity=2)
