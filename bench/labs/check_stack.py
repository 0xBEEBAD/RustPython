"""Print the PE SizeOfStackReserve of one or more Windows binaries.

PGO builds lose the /STACK:8000000 link flag if RUSTFLAGS is set without
repeating it, and the 1 MB MSVC default then trips the native stack guard
through deep non-tail *args/**kwargs calls. Expect 0x7a1200.
"""
import struct
import sys


def stack_reserve(path):
    with open(path, "rb") as f:
        head = f.read(4096)
    pe = struct.unpack_from("<I", head, 0x3C)[0]
    magic = struct.unpack_from("<H", head, pe + 24)[0]
    if magic == 0x20B:
        return hex(magic), struct.unpack_from("<Q", head, pe + 24 + 72)[0]
    if magic == 0x10B:
        return hex(magic), struct.unpack_from("<I", head, pe + 24 + 64)[0]
    return None, None


for path in sys.argv[1:]:
    magic, size = stack_reserve(path)
    print("%-52s magic=%s reserve=%s %s" % (path, magic, hex(size) if size else "?",
                                            "OK" if size == 0x7A1200 else "CHECK"))
