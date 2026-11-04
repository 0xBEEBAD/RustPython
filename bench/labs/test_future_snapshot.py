"""Pin CPython 3.15's `concurrent.futures.Future._get_snapshot()`.

3.15 added one atomic state read to `Future`
(`Lib/concurrent/futures/_base.py:_get_snapshot`) and made
`asyncio.futures._copy_future_state` use it instead of `done()`/`cancelled()`/
`result()`/`exception()` - four lock acquisitions become one. asyncio's
`test_futures.py` calls this "the optimized path using `_get_snapshot` when
available", so the tuple contract has to be exact.

    python bench/labs/test_future_snapshot.py
"""

import unittest
from concurrent.futures import Future


class TestFutureSnapshot(unittest.TestCase):
    def test_pending(self):
        f = Future()
        done, cancelled, result, exception = f._get_snapshot()
        self.assertEqual((done, cancelled), (False, False))
        self.assertIsNone(result)
        self.assertIsNone(exception)

    def test_finished_with_result(self):
        f = Future()
        f.set_result(42)
        done, cancelled, result, exception = f._get_snapshot()
        self.assertEqual((done, cancelled), (True, False))
        self.assertEqual(result, 42)
        self.assertIsNone(exception)

    def test_finished_with_exception(self):
        f = Future()
        exc = ValueError("test error")
        f.set_exception(exc)
        done, cancelled, result, exception = f._get_snapshot()
        self.assertEqual((done, cancelled), (True, False))
        self.assertIsNone(result)
        self.assertIs(exception, exc)

    def test_cancelled(self):
        f = Future()
        self.assertTrue(f.cancel())
        done, cancelled, result, exception = f._get_snapshot()
        self.assertEqual((done, cancelled), (True, True))
        self.assertIsNone(result)
        self.assertIsNone(exception)

    def test_running_is_not_done(self):
        f = Future()
        f.set_running_or_notify_cancel()
        done, cancelled, result, exception = f._get_snapshot()
        self.assertEqual((done, cancelled), (False, False))
        self.assertIsNone(result)
        self.assertIsNone(exception)


if __name__ == "__main__":
    unittest.main(verbosity=2)
