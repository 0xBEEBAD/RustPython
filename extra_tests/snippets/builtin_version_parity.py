"""The interpreter must self-report the CPython version it targets.

The parity target is CPython 3.15.2 final. `sys.hexversion` is packed with
CPython's formula (`patchlevel.h`: major<<24 | minor<<16 | micro<<8 |
release_level<<4 | serial, with final = 0xF), so a wrong release-level code
surfaces here even when `sys.version_info` looks right.
"""

import sys
import unittest

TARGET = (3, 15, 2, "final", 0)
# (3 << 24) | (15 << 16) | (2 << 8) | (0xF << 4) | 0
HEXVERSION = 0x030F02F0
LEVEL_CODES = {"alpha": 0xA, "beta": 0xB, "candidate": 0xC, "final": 0xF}


class VersionParityTest(unittest.TestCase):
    def test_version_info(self):
        import sys

        self.assertEqual(tuple(sys.version_info), TARGET)

    def test_hexversion_packing(self):
        import sys

        info = sys.version_info
        packed = (
            (info.major << 24)
            | (info.minor << 16)
            | (info.micro << 8)
            | (LEVEL_CODES[info.releaselevel] << 4)
            | info.serial
        )
        self.assertEqual(sys.hexversion, packed)
        self.assertEqual(sys.hexversion, HEXVERSION)

    def test_version_string(self):
        import sys

        # A final release carries no level suffix, and the MSC-annotated first
        # line is what platform.py parses.
        self.assertTrue(sys.version.startswith("3.15.2 "), sys.version.splitlines()[0])
        self.assertEqual(sys.version.split()[0], "3.15.2")

    def test_platform_views(self):
        import platform

        self.assertEqual(platform.python_version(), "3.15.2")
        self.assertEqual(platform.python_version_tuple(), ("3", "15", "2"))

    def test_config_views(self):
        import sys
        import sysconfig

        self.assertEqual(sys.implementation.cache_tag, "cpython-315")
        self.assertEqual(sysconfig.get_config_var("py_version_short"), "3.15")

    @unittest.skipUnless(sys.platform == "win32", "Windows extension naming")
    def test_extension_tag_lags(self):
        # The extension tag names the ABI this checkout can actually load: the
        # prebuilt test extensions and the import library are cp314, so the tag
        # deliberately lags the reported language version.
        import sysconfig

        soabi = sysconfig.get_config_var("SOABI")
        self.assertEqual(soabi, "cp314-win_amd64")
        self.assertEqual(
            sysconfig.get_config_var("EXT_SUFFIX"), f".{soabi}.pyd"
        )


if __name__ == "__main__":
    unittest.main()
