"""What version do we claim to be, and is the encoding CPython's?

Run this on the reference interpreter first; it prints the facts a parity test
should assert. Two things are checked: the reported tuple/string, and whether
our hexversion formula matches CPython's `_Py_PACK_FULL_VERSION`
(major<<24 | minor<<16 | micro<<8 | (level&0xf)<<4 | (serial&0xf)), including
the level code itself (alpha 0xA, beta 0xB, candidate 0xC, final 0xF).
"""

import sys

LEVEL_CODES = {"alpha": 0xA, "beta": 0xB, "candidate": 0xC, "final": 0xF}


def expected_hex(info):
    level = LEVEL_CODES[info.releaselevel]
    return (
        (info.major << 24)
        | (info.minor << 16)
        | (info.micro << 8)
        | (level << 4)
        | (info.serial & 0xF)
    )


print("sys.version           :", sys.version)
print("sys.version_info      :", sys.version_info)
print("sys.hexversion        :", hex(sys.hexversion))
print("expected hexversion   :", hex(expected_hex(sys.version_info)))
print("hexversion matches    :", sys.hexversion == expected_hex(sys.version_info))
print("implementation        :", sys.implementation.name, sys.implementation.version)

import sysconfig

for key in ("py_version_short", "py_version_nodots", "EXT_SUFFIX", "SOABI"):
    print(f"sysconfig[{key!r}]".ljust(24), ":", sysconfig.get_config_var(key))

import _imp

print("_imp.extension_suffixes():", _imp.extension_suffixes())
print("maxsize/64bit           :", sys.maxsize == 2**63 - 1)
