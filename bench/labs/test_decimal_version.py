"""Pin CPython 3.15's deprecated `__version__` behaviour for decimal.

Reference is the 3.15 source, not the local 3.14.7 interpreter: 3.15 moved
`__version__` out of the module dict and answers it from a module-level
`__getattr__` that warns (`Modules/_decimal/_decimal.c:decimal_getattr`,
`Lib/_pydecimal.py:__getattr__`, `Lib/decimal.py` re-exporting it). CPython's own
test is `test_decimal.TestModule.test_deprecated__version__`, which also asserts
the warning is attributed to the caller's file.

    python bench/labs/test_decimal_version.py

Rows that this fork does not implement yet fail, which is the point.
"""

import unittest


class TestVersionDeprecation:
    """The shared body CPython uses for the C and pure-Python modules."""

    # The name the AttributeError must report, which is `decimal` for the C
    # module (hardcoded in C) and the module's own name for _pydecimal.
    error_module = None

    def test_version_is_not_a_module_attribute(self):
        # A boolean rather than assertNotIn(..., vars(module)), so a failure
        # prints one line instead of the whole module dictionary.
        self.assertEqual("__version__" in vars(self.module), False)

    def test_spec_version_is_the_real_attribute(self):
        self.assertEqual(self.module.SPEC_VERSION, "1.70")

    def test_deprecated__version__(self):
        with self.assertWarnsRegex(
            DeprecationWarning,
            "'__version__' is deprecated and slated for removal in Python 3.20",
        ) as cm:
            value = getattr(self.module, "__version__")
        self.assertEqual(value, "1.70")
        self.assertEqual(cm.filename, __file__)

    def test_unknown_attribute_names_the_module(self):
        with self.assertRaises(AttributeError) as cm:
            self.module.zzzq
        self.assertEqual(
            str(cm.exception),
            f"module {self.error_module!r} has no attribute 'zzzq'",
        )


class CTestVersionDeprecation(TestVersionDeprecation, unittest.TestCase):
    def setUp(self):
        import _decimal as module

        self.module = module
        self.error_module = "decimal"


class DecimalTestVersionDeprecation(TestVersionDeprecation, unittest.TestCase):
    def setUp(self):
        import decimal as module

        self.module = module
        self.error_module = "decimal"


class PyTestVersionDeprecation(TestVersionDeprecation, unittest.TestCase):
    def setUp(self):
        import _pydecimal as module

        self.module = module
        # `_pydecimal` rebinds `__name__ = 'decimal'` for pickling, so 3.15's
        # `f"module {__name__!r}"` message names decimal here too.
        self.error_module = "decimal"


if __name__ == "__main__":
    unittest.main(verbosity=2)
