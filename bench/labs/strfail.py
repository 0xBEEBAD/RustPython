import unittest
import test.test_str as ts
suite = unittest.TestSuite()
suite.addTest(ts.StrTest("test_lower"))
suite.addTest(ts.StrTest("test_upper"))
r = unittest.TextTestRunner(verbosity=2).run(suite)
