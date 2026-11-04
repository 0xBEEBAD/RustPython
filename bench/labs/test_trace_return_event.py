"""Return trace events for frames that started before tracing began.

Reference behaviour, read from CPython 3.14.7 by running these shapes there
(the sequences below are what the reference actually emits):

  * `sys.settrace()` called mid-frame with no `f_trace` produces NO events for
    that frame - on either interpreter, so nothing here asserts otherwise.
  * once the frame's own `f_trace` is set - which is what bdb/pdb do - the frame
    emits its line events and then, at exit, `('return', name, returned_value)`;
    unwinding emits `('exception', ...)` followed by `('return', name, None)`.
  * a frame entered while the tracer was already installed emits exactly one
    call and one return.
  * a generator frame reports every resume: `('call', name, None)` then
    `('return', name, <yielded value>)`, and `('return', name, None)` once it is
    exhausted - CPython surfaces `PyTrace_YRETURN` as a plain `'return'` event
    that carries the yielded value, and the `return 42` value as the arg of the
    final `'return'` (measured on 3.14.7: `('return','g',1)`, `('return','g',42)`).

RustPython chose the traced wrapper at call time, so a frame that started
untraced ran on the fast route: line events fire (re-checked per instruction)
but the exit event never did, which is why Lib/test/test_pdb.py lost its
`--Return--` stops in three doctests.
"""
import sys
import unittest


class TraceReturnTest(unittest.TestCase):
    def setUp(self):
        self.events = []
        self._old = sys.gettrace()

    def tearDown(self):
        sys.settrace(self._old)

    def tracer(self, frame, event, arg):
        self.events.append((event, frame.f_code.co_name, arg))
        return self.tracer

    def test_return_event_for_frame_entered_untraced(self):
        def target():
            sys.settrace(self.tracer)
            sys._getframe().f_trace = self.tracer
            value = 2
            return value

        self.assertEqual(target(), 2)
        sys.settrace(None)
        self.assertTrue(
            [e for e in self.events if e[0] == "line"],
            f"expected line events once f_trace was set: {self.events}",
        )
        self.assertIn(
            ("return", "target", 2),
            self.events,
            f"missing or wrong return event: {self.events}",
        )

    def test_unwind_reports_return_after_exception(self):
        def raiser():
            sys.settrace(self.tracer)
            sys._getframe().f_trace = self.tracer
            raise RuntimeError("boom")

        with self.assertRaises(RuntimeError):
            raiser()
        sys.settrace(None)
        # unittest's own frames get events once the tracer is installed, so
        # look at the raiser frame's stream only.
        mine = [e for e in self.events if e[1] == "raiser"]
        kinds = [event for event, _, _ in mine]
        self.assertIn("exception", kinds, self.events)
        self.assertEqual(
            mine[-1],
            ("return", "raiser", None),
            f"the frame's last event must be the unwinding return: {mine}",
        )

    def test_no_double_return_event(self):
        counts = {"call": 0, "return": 0}

        def tracer(frame, event, arg):
            if frame.f_code.co_name == "callee" and event in counts:
                counts[event] += 1
            return tracer

        def callee():
            return 7

        sys.settrace(tracer)
        self.assertEqual(callee(), 7)
        sys.settrace(None)
        self.assertEqual(counts["call"], 1, counts)
        self.assertEqual(counts["return"], 1, counts)

    def test_nested_frames_unaffected(self):
        def outer():
            sys.settrace(self.tracer)
            sys._getframe().f_trace = self.tracer
            return inner()

        def inner():
            return 42

        self.assertEqual(outer(), 42)
        sys.settrace(None)
        self.assertIn(("return", "inner", 42), self.events, self.events)
        outer_events = [e for e in self.events if e[1] == "outer"]
        self.assertEqual(outer_events[-1][0], "return", outer_events)

    def test_untraced_frame_entered_before_settrace_reports_nothing(self):
        # The mirror image of the first test: a frame that was already running
        # when the tracer was installed, and never set `f_trace`, reports
        # neither line nor return events on either interpreter. Firing a return
        # for every fast-route exit is what broke bdb's event sequences.
        def quiet():
            sys.settrace(self.tracer)
            return 1

        self.assertEqual(quiet(), 1)
        sys.settrace(None)
        mine = [e for e in self.events if e[1] == "quiet"]
        self.assertEqual(mine, [], f"an untraced frame must report nothing: {mine}")

    def test_generator_resume_reports_the_yielded_value(self):
        def g():
            yield 1
            yield 2

        sys.settrace(self.tracer)
        try:
            self.assertEqual(list(g()), [1, 2])
        finally:
            sys.settrace(None)
        mine = [e for e in self.events if e[1] == "g" and e[0] == "return"]
        self.assertEqual(
            mine,
            [("return", "g", 1), ("return", "g", 2), ("return", "g", None)],
            f"every resume must report what it handed the caller: {self.events}",
        )

    def test_generator_return_value_replaces_stopiteration_arg(self):
        def g():
            yield 1
            return 42

        sys.settrace(self.tracer)
        try:
            it = g()
            self.assertEqual(next(it), 1)
            with self.assertRaises(StopIteration) as ctx:
                next(it)
        finally:
            sys.settrace(None)
        self.assertEqual(ctx.exception.value, 42)
        mine = [e for e in self.events if e[1] == "g" and e[0] == "return"]
        self.assertEqual(
            mine,
            [("return", "g", 1), ("return", "g", 42)],
            f"the closing resume reports the return value: {self.events}",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
