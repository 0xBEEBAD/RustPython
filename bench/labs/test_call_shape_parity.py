"""Call-shape parity probe: pins the observable behavior of every CALL shape
that the interpreter's argument-passing paths branch on. Must pass on both
CPython and RustPython, and must pass BEFORE and AFTER a change to
execute_call_vectorcall -- it is the invariant the refactor is not allowed to
break, not a test of the refactor itself.
"""
import gc
import sys
import unittest


class TestFastPathShapes(unittest.TestCase):
    """Plain Python function, exact positional arity: the borrowed-args path."""

    def test_exact_positional(self):
        def f(a, b):
            return a + b
        self.assertEqual(f(1, 2), 3)
        self.assertEqual(f("x", "y"), "xy")

    def test_zero_arg(self):
        def g():
            return 42
        self.assertEqual(g(), 42)

    def test_many_args_beyond_stack_buffer(self):
        # Arity above the small-argument buffer must still bind correctly.
        def f(a1, a2, a3, a4, a5, a6, a7, a8, a9, a10):
            return [a1, a2, a3, a4, a5, a6, a7, a8, a9, a10]
        self.assertEqual(f(*range(10)), list(range(10)))

    def test_retained_arguments(self):
        # A callee that keeps its arguments must not observe a dropped object.
        kept = []

        def f(a, b):
            kept.append(a)
            kept.append(b)
            return None
        probe = []
        f(probe, {"k": probe})
        self.assertIs(kept[0], probe)
        self.assertIs(kept[1]["k"], probe)

    def test_arity_mismatch_is_typeerror(self):
        def f(a, b):
            return a
        with self.assertRaises(TypeError):
            f(1)
        with self.assertRaises(TypeError):
            f(1, 2, 3)


class TestGenericPathShapes(unittest.TestCase):
    """Every shape that must fall through to the owned argument vector."""

    def test_varargs(self):
        def f(a, *rest):
            return a, rest
        self.assertEqual(f(1, 2, 3), (1, (2, 3)))
        self.assertEqual(f(1), (1, ()))

    def test_varkwargs(self):
        def f(**kw):
            return kw
        self.assertEqual(f(a=1, b=2), {"a": 1, "b": 2})

    def test_kwonly(self):
        def f(a, *, b):
            return a, b
        self.assertEqual(f(1, b=2), (1, 2))
        with self.assertRaises(TypeError):
            f(1, 2)

    def test_defaults(self):
        def f(a, b=10):
            return a, b
        self.assertEqual(f(1), (1, 10))
        self.assertEqual(f(1, 2), (1, 2))

    def test_generator_function_is_not_run(self):
        def gen(n):
            yield n
        g = gen(5)
        self.assertTrue(hasattr(g, "__next__"))
        self.assertEqual(list(g), [5])

    def test_generator_with_varargs(self):
        def gen(*args):
            yield from args
        self.assertEqual(list(gen(1, 2, 3)), [1, 2, 3])

    def test_coroutine_shape(self):
        async def coro(a):
            return a * 2
        import asyncio
        self.assertEqual(asyncio.run(coro(3)), 6)

    def test_builtin_varargs(self):
        self.assertEqual(max(1, 5, 3), 5)
        self.assertEqual(min([4, 2, 9]), 2)
        self.assertEqual(int("ff", base=16), 255)

    def test_bound_method_of_builtin(self):
        lst = []
        lst.append(1)
        lst.extend([2, 3])
        lst.insert(0, 0)
        self.assertEqual(lst, [0, 1, 2, 3])
        d = {}
        d.setdefault("a", 1)
        d.update({"b": 2})
        self.assertEqual(d, {"a": 1, "b": 2})

    def test_class_call_with_init(self):
        class C:
            def __init__(self, a, b=0):
                self.a, self.b = a, b
        self.assertEqual((C(1).a, C(1, 2).b), (1, 2))

    def test_class_call_no_init(self):
        class D:
            pass
        self.assertIsInstance(D(), D)

    def test_class_with_new(self):
        class E:
            def __new__(cls, v):
                self = super().__new__(cls)
                self.v = v
                return self
        self.assertEqual(E(7).v, 7)

    def test_callable_object(self):
        class F:
            def __call__(self, x):
                return x + 1
        self.assertEqual(F()(1), 2)

    def test_star_args_unpacking(self):
        def f(a, b, c):
            return a, b, c
        args = (1, 2, 3)
        self.assertEqual(f(*args), args)
        self.assertEqual(f(*[*args]), args)

    def test_type_call_builtin(self):
        self.assertEqual(str(1), "1")
        self.assertEqual(float("1.5"), 1.5)
        self.assertEqual(list(range(3)), [0, 1, 2])
        self.assertEqual(dict(a=1), {"a": 1})
        self.assertEqual(tuple([1, 2]), (1, 2))


class TestErrorAndUnwind(unittest.TestCase):
    """Stack slots must be released exactly once, even when the callee raises."""

    def test_exception_propagates_with_frame(self):
        def inner(x):
            raise ValueError(x)
        # Capture the traceback inside the handler: both interpreters drop the
        # frame chain once the raising scope is gone, so asserting on
        # cm.exception.__traceback__ afterwards would compare frame lifetime
        # rules rather than call behavior.
        caught = []
        try:
            inner(9)
        except ValueError as e:
            tb = e.__traceback__
            names = []
            while tb is not None:
                names.append(tb.tb_frame.f_code.co_name)
                tb = tb.tb_next
            caught.append((e.args, names))
        self.assertEqual(caught[0][0], (9,))
        self.assertEqual(caught[0][1][-1], "inner")
        # the caller frame must still be intact and usable
        self.assertEqual(len([1]), 1)

    def test_stack_recovers_after_raise(self):
        def boom():
            raise RuntimeError
        for _ in range(200):
            try:
                boom()
            except RuntimeError:
                pass
        self.assertEqual(sum(range(5)), 10)
        lst = []
        for i in range(50):
            try:
                lst.append(i)
                boom()
            except RuntimeError:
                pass
        self.assertEqual(len(lst), 50)

    def test_nested_calls_after_raise(self):
        def a(x):
            return b(x)

        def b(x):
            if x:
                raise ZeroDivisionError
            return x
        for i in range(100):
            try:
                a(1)
            except ZeroDivisionError:
                pass
        self.assertEqual(a(0), 0)


class TestRefcounts(unittest.TestCase):
    """Argument ownership must be exact: no leak, no premature free."""

    def test_arg_refcount_stable(self):
        def f(a, b):
            return a
        o = object()
        r0 = sys.getrefcount(o)
        for _ in range(1000):
            f(o, o)
        self.assertEqual(sys.getrefcount(o), r0)

    def test_builtin_arg_refcount_stable(self):
        o = []
        r0 = sys.getrefcount(o)
        for _ in range(1000):
            len(o)
            bool(o)
        self.assertEqual(sys.getrefcount(o), r0)

    def test_retained_arg_survives(self):
        store = []

        def f(a):
            store.append(a)
        for i in range(200):
            f([i])
        self.assertEqual([x[0] for x in store[:200]], list(range(200)))
        del store[:]
        gc.collect()

    def test_no_resurrection_loop(self):
        class Z:
            pass
        for _ in range(2000):
            Z()
        gc.collect()


class TestTracingDisabledFastPath(unittest.TestCase):
    """Under sys.settrace the interpreter must observe every call event."""

    def test_call_events_under_trace(self):
        events = []

        def tracer(frame, event, arg):
            events.append((event, frame.f_code.co_name))
            return None

        def target(a, b):
            return a + b

        def builtin_target(x):
            return len(x)

        sys.settrace(tracer)
        try:
            target(1, 2)
            builtin_target([1, 2, 3])
        finally:
            sys.settrace(None)
        calls = [name for event, name in events if event == "call"]
        self.assertIn("target", calls)
        self.assertIn("builtin_target", calls)
        # locals must be visible and correct from the traced frame
        seen = {}

        def tracer2(frame, event, arg):
            if event == "call" and frame.f_code.co_name == "g":
                seen.update(dict(frame.f_locals))
            return None

        def g(p, q):
            return p, q
        sys.settrace(tracer2)
        try:
            g(1, 2)
        finally:
            sys.settrace(None)
        self.assertEqual(seen, {"p": 1, "q": 2})


if __name__ == "__main__":
    unittest.main(verbosity=2)
