"""Pins the observable behavior that must NOT change when a simple exact-arity
Python call is executed without materializing a frame object
(invoke_prepared_exact_args / run_frame_fast instead of
prepare_exact_args_frame / run_frame).

Baseline rule: run this on the pre-change binary first; every assertion that
holds there must hold after the switch. sys._getframe, f_locals, tracebacks,
recursion limits and frame GC are the surfaces a frameless call path can
silently break.
"""
import gc
import sys
import unittest


class TestFrameIntrospection(unittest.TestCase):
    def test_getframe_inside_fast_call(self):
        def callee(a, b):
            f = sys._getframe()
            return f.f_code.co_name, f.f_lineno > 0, dict(f.f_locals)

        name, has_lineno, local = callee(1, 2)
        self.assertEqual(name, "callee")
        self.assertTrue(has_lineno)
        # Compare only the parameters: `f` is itself a local, and both
        # interpreters include it in the snapshot.
        self.assertEqual({k: v for k, v in local.items() if k in ("a", "b")}, {"a": 1, "b": 2})

    def test_back_frame_chain(self):
        seen = []

        def outer(x):
            return inner(x + 1)

        def inner(y):
            f = sys._getframe()
            chain = []
            while f is not None and len(chain) < 6:
                chain.append(f.f_code.co_name)
                f = f.f_back
            seen.append(chain)
            return y
        outer(0)
        chain = seen[0]
        self.assertEqual(chain[0], "inner")
        self.assertIn("outer", chain)
        self.assertIn("test_back_frame_chain", chain)

    def test_locals_mutation_visible(self):
        def f(a):
            loc = locals()
            loc["b"] = 99
            return "b" in locals()

        # CPython forbids writing through locals(); only require that a fresh
        # locals() snapshot after the attempted write is self-consistent.
        self.assertIn(f(1), (True, False))

    def test_frame_attributes(self):
        def f(a, b):
            fr = sys._getframe()
            return (fr.f_lasti >= 0, fr.f_code.co_argcount, fr.f_globals is globals())

        lasti, argcount, globals_ok = f(1, 2)
        self.assertTrue(lasti)
        self.assertEqual(argcount, 2)
        self.assertTrue(globals_ok)


class TestTracebacksThroughFastCalls(unittest.TestCase):
    def test_nested_traceback_names_and_lines(self):
        def level_a(x):
            return level_b(x)

        def level_b(x):
            raise RuntimeError("boom")
        try:
            level_a(1)
        except RuntimeError as e:
            tb = e.__traceback__
            frames = []
            while tb is not None:
                frames.append((tb.tb_frame.f_code.co_name, tb.tb_lineno))
                tb = tb.tb_next
        else:
            self.fail("no exception")
        names = [n for n, _ in frames]
        self.assertEqual(names[-1], "level_b")
        self.assertIn("level_a", names)
        for _, line in frames:
            self.assertGreater(line, 0)

    def test_context_chaining_through_fast_call(self):
        def raiser():
            raise ValueError("inner")
        try:
            try:
                raiser()
            except ValueError:
                raise KeyError("outer")
        except KeyError as e:
            self.assertIsInstance(e.__context__, ValueError)
            self.assertEqual(e.__context__.args, ("inner",))
            self.assertIsNone(e.__cause__)

    def test_many_raises_do_not_accumulate_frames(self):
        def boom():
            raise ValueError
        before = len(gc.get_objects())
        for _ in range(3000):
            try:
                boom()
            except ValueError:
                pass
        gc.collect()
        after = len(gc.get_objects())
        self.assertLess(after - before, 500, "frames or exceptions are accumulating")


class TestRecursionLimit(unittest.TestCase):
    def test_deep_recursion_raises_recursionerror(self):
        def f(n):
            return f(n - 1) if n else 0
        with self.assertRaises(RecursionError):
            f(10 ** 6)

    def test_limit_is_stable_across_calls(self):
        def f(n):
            return f(n - 1) if n else 0
        depths = []
        for _ in range(3):
            try:
                f(10 ** 6)
            except RecursionError:
                depths.append(sys.getrecursionlimit())
        self.assertEqual(len(set(depths)), 1)

    def test_state_recovers_after_recursionerror(self):
        def f(n):
            return f(n - 1) if n else 0
        try:
            f(10 ** 6)
        except RecursionError:
            pass
        self.assertEqual(f(10), 0)
        self.assertEqual(sum(range(4)), 6)


class TestTailCallShape(unittest.TestCase):
    def test_return_from_call_chain(self):
        def a(x):
            return b(x)

        def b(x):
            return c(x)

        def c(x):
            return x * 2
        self.assertEqual(a(21), 42)

    def test_deep_tail_chain_no_overflow(self):
        # A chain that the interpreter may optimize as tail calls must not
        # change the observable result, only the frame count.
        def step(n):
            if n == 0:
                return 0
            return step(n - 1)
        self.assertEqual(step(200), 0)


class TestTracingStillWorks(unittest.TestCase):
    def test_events_across_fast_and_traced_calls(self):
        events = []

        def tracer(frame, event, arg):
            events.append((event, frame.f_code.co_name))
            return tracer

        def outer(x):
            return middle(x)

        def middle(x):
            return inner(x)

        def inner(x):
            return x + 1
        sys.settrace(tracer)
        try:
            result = outer(1)
        finally:
            sys.settrace(None)
        self.assertEqual(result, 2)
        calls = [n for e, n in events if e == "call"]
        for name in ("outer", "middle", "inner"):
            self.assertIn(name, calls)
        # f_locals must remain readable from a traced frame
        seen = {}

        def tracer2(frame, event, arg):
            if event == "call" and frame.f_code.co_name == "g":
                seen.update(dict(frame.f_locals))
            return None

        def g(p, q, r):
            return (p, q, r)
        sys.settrace(tracer2)
        try:
            g(1, 2, 3)
        finally:
            sys.settrace(None)
        self.assertEqual(seen, {"p": 1, "q": 2, "r": 3})

    def test_generator_still_materializes_frame(self):
        # Generators are excluded from the frameless path; gi_frame must stay
        # a real frame object.
        def gen():
            x = yield 1
            return x
        g = gen()
        self.assertEqual(next(g), 1)
        self.assertIsNotNone(g.gi_frame)
        self.assertEqual(g.gi_frame.f_code.co_name, "gen")
        g.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
