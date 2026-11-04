"""Walking another thread's exception traceback from this thread.

`sys._current_exceptions()` hands out exception objects captured in *other*
threads. A user then does what `Lib/test/test_sys.py::test_current_exceptions`
does - `traceback.extract_stack(exc.__traceback__.tb_frame)` - and expects to see
that thread's whole call stack. CPython gets that for free because every frame
carries a real `f_back`; this fork keeps frames as lightweight per-thread
`InterpreterFrame`s and materializes `FrameObject`s lazily, so a foreign chain is
invisible until it is materialized and linked.

Expectations below are CPython 3.14 behaviour - run this file there first.
"""
import gc
import sys
import threading
import traceback
import unittest


class CrossThreadExceptionsTest(unittest.TestCase):
    def setUp(self):
        self.raised = threading.Event()
        self.leave = threading.Event()
        self.exc = None
        self.frames = []

    def _start(self, target):
        t = threading.Thread(target=target)
        t.start()
        self.assertTrue(self.raised.wait(timeout=30), "thread never reached the except block")
        return t

    def _worker(self):
        def g456():
            try:
                raise RuntimeError("boom")
            except RuntimeError as e:
                self.exc = e
                self.raised.set()
                self.leave.wait()

        def f123():
            g456()

        f123()

    def test_foreign_traceback_walks_whole_stack(self):
        t = self._start(self._worker)
        try:
            tid = t.ident
            d = sys._current_exceptions()
            self.assertIn(tid, d, d)
            exc = d[tid]
            self.assertIs(exc, self.exc)
            stack = traceback.extract_stack(exc.__traceback__.tb_frame)
            names = [entry.name for entry in stack]
            self.assertIn("f123", names, f"foreign chain stops early: {names}")
            i = names.index("f123")
            self.assertEqual(stack[i].line.strip(), "g456()")
            self.assertEqual(stack[i + 1].name, "g456")
            # A live frame reports the line it is blocked on, not the raise line.
            self.assertStartsWith(stack[i + 1].line, ("self.leave.wait()",))
        finally:
            self.leave.set()
            t.join()

    def test_one_frame_object_per_stack_level(self):
        t = self._start(self._worker)
        try:
            tid = t.ident
            exc = sys._current_exceptions()[tid]
            tb_frame = exc.__traceback__.tb_frame
            top = sys._current_frames()[tid]
            chain = []
            frame = top
            while frame is not None:
                chain.append(frame)
                self.assertLess(len(chain), 100, "frame chain does not terminate")
                frame = frame.f_back
            self.assertIn(tb_frame, chain, "the traceback frame is a second object")
            self.assertEqual(
                len({id(f) for f in chain}),
                len(chain),
                f"one stack level, one frame object: {chain}",
            )
        finally:
            self.leave.set()
            t.join()

    def test_dead_thread_leaves_no_entry_and_its_frames_stay_walkable(self):
        # Frames are not weakref-able on CPython, so the observable contract is
        # the two registries plus what a traceback kept alive by the program can
        # still show after its thread is gone.
        keep = []
        ready = threading.Event()

        def worker():
            try:
                raise ValueError("gone")
            except ValueError as e:
                keep.append((e, e.__traceback__.tb_frame))
                ready.set()

        t = threading.Thread(target=worker)
        t.start()
        self.assertTrue(ready.wait(timeout=30))
        tid = t.ident
        t.join()
        gc.collect()
        self.assertNotIn(tid, sys._current_exceptions(), sys._current_exceptions())
        self.assertNotIn(tid, sys._current_frames(), sys._current_frames())
        exc, frame = keep[0]
        self.assertIs(exc.__class__, ValueError)
        names = [entry.name for entry in traceback.extract_stack(frame)]
        # CPython keeps the whole (now exited) chain reachable from a traceback
        # the program holds: _bootstrap -> _bootstrap_inner -> run -> worker.
        self.assertEqual(names[-1], "worker", f"a kept traceback ends at its frame: {names}")
        self.assertIn("_bootstrap_inner", names, f"dead thread's chain was cut: {names}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
