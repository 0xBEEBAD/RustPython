"""Behavior pinned for the defaulted-positional-call fast path.

`LUNA_ABLATE=defbind` must not change any answer here: the fast path only skips
the generic binder's machinery, it does not decide anything the binder decides.
So this file is the regression test for both routes -- run it with the fast path
live and with it ablated, and the results must be identical to each other and to
CPython.

Run against CPython first; every expectation below is what CPython prints.
"""

import unittest


def one(a=1):
    return a


def two(a, b=2):
    return (a, b)


def three(a, b=2, c=3):
    return (a, b, c)


def all_defaulted(a=1, b=2):
    return (a, b)


def posonly(a, /, b=2):
    return (a, b)


def kwonly(a, *, b=2):
    return (a, b)


def varargs(a, b=2, *rest):
    return (a, b, rest)


def varkw(a, b=2, **kw):
    return (a, b, kw)


def gen(a, b=2):
    yield (a, b)


def counter(n, acc=0):
    if n == 0:
        return acc
    return counter(n - 1, acc + n)


def outer(x):
    def inner(a=1):
        return (a, x)

    return inner


class Defaults(unittest.TestCase):
    def test_default_used(self):
        self.assertEqual(one(), 1)
        self.assertEqual(two(1), (1, 2))
        self.assertEqual(three(1), (1, 2, 3))
        self.assertEqual(three(1, 5), (1, 5, 3))
        self.assertEqual(all_defaulted(), (1, 2))

    def test_given_values_are_not_replaced(self):
        self.assertEqual(two(1, 9), (1, 9))
        self.assertEqual(three(1, 9, 8), (1, 9, 8))

    def test_missing_required_positional(self):
        def f(a, b, c=3):
            return (a, b, c)

        with self.assertRaises(TypeError) as ctx:
            f(1)
        self.assertIn(
            "f() missing 1 required positional argument: 'b'", str(ctx.exception)
        )
        with self.assertRaises(TypeError) as ctx:
            f()
        self.assertIn(
            "f() missing 2 required positional arguments: 'a' and 'b'",
            str(ctx.exception),
        )

    def test_too_many_positional(self):
        with self.assertRaises(TypeError) as ctx:
            three(1, 2, 3, 4)
        self.assertIn(
            "three() takes from 1 to 3 positional arguments but 4 were given",
            str(ctx.exception),
        )

    def test_too_many_positional(self):
        with self.assertRaises(TypeError) as ctx:
            three(1, 2, 3, 4)
        self.assertIn(
            "three() takes from 1 to 3 positional arguments but 4 were given",
            str(ctx.exception),
        )

    def test_too_many_positional_no_defaults(self):
        def g(a, b):
            return (a, b)

        with self.assertRaises(TypeError) as ctx:
            g(1, 2, 3)
        self.assertIn("g() takes 2 positional arguments but 3 were given", str(ctx.exception))

    def test_defaults_are_read_live(self):
        def f(a, b=1, c=2):
            return (a, b, c)

        self.assertEqual(f(0), (0, 1, 2))
        # `__defaults__` aligns to the *last* parameters, so a shorter tuple
        # leaves a required parameter out rather than filling the front.
        f.__defaults__ = (9,)
        with self.assertRaises(TypeError) as ctx:
            f(0)
        self.assertIn("f() missing 1 required positional argument: 'b'", str(ctx.exception))
        f.__defaults__ = (8, 9)
        self.assertEqual(f(0), (0, 8, 9))
        f.__defaults__ = None
        with self.assertRaises(TypeError) as ctx:
            f(0)
        self.assertIn("f() missing 2 required positional arguments", str(ctx.exception))
        f.__defaults__ = (7, 8, 9)
        self.assertEqual(f(0), (0, 8, 9))
        self.assertEqual(f(0, 5), (0, 5, 9))

    def test_default_object_identity_is_shared(self):
        def accum(a=[]):
            a.append(1)
            return a

        first = accum()
        self.assertEqual(first, [1])
        second = accum()
        self.assertIs(first, second)
        self.assertEqual(second, [1, 1])
        self.assertIs(accum.__defaults__[0], first)
        accum.__defaults__ = None

    def test_positional_only_with_default(self):
        # `b` is a normal parameter here, so naming it is legal.
        self.assertEqual(posonly(1), (1, 2))
        self.assertEqual(posonly(1, b=5), (1, 5))

    def test_positional_only_parameter_named(self):
        def f(a=1, /, b=2):
            return (a, b)

        self.assertEqual(f(), (1, 2))
        self.assertEqual(f(5), (5, 2))
        with self.assertRaises(TypeError) as ctx:
            f(a=9)
        self.assertIn("f() got some positional-only arguments passed", str(ctx.exception))

    def test_keyword_for_defaulted_parameter(self):
        self.assertEqual(two(1, b=9), (1, 9))
        self.assertEqual(two(a=1), (1, 2))
        self.assertEqual(two(b=9, a=1), (1, 9))

    def test_keyword_only_is_unaffected(self):
        self.assertEqual(kwonly(1), (1, 2))
        self.assertEqual(kwonly(1, b=5), (1, 5))
        with self.assertRaises(TypeError) as ctx:
            kwonly(1, 2, 3)
        self.assertIn("kwonly() takes 1 positional argument but 3 were given", str(ctx.exception))

    def test_varargs_and_varkw_still_bind(self):
        self.assertEqual(varargs(1), (1, 2, ()))
        self.assertEqual(varargs(1, 5, 6, 7), (1, 5, (6, 7)))
        self.assertEqual(varkw(1), (1, 2, {}))
        self.assertEqual(varkw(1, 5, x=6), (1, 5, {"x": 6}))

    def test_generator_with_default(self):
        g = gen(1)
        self.assertEqual(next(g), (1, 2))
        g2 = gen(1, 3)
        self.assertEqual(next(g2), (1, 3))

    def test_recursion_through_defaults(self):
        self.assertEqual(counter(4), 10)
        self.assertEqual(counter(4, 100), 110)

    def test_closure_with_default(self):
        f = outer(7)
        self.assertEqual(f(), (1, 7))
        self.assertEqual(f(2), (2, 7))

    def test_bound_method_defaults(self):
        class C:
            def m(self, a=1, b=2):
                return (self, a, b)

            def n(self, *args, **kw):
                return (args, kw)

        c = C()
        self.assertEqual(c.m(), (c, 1, 2))
        self.assertEqual(c.m(9), (c, 9, 2))
        self.assertEqual(c.m(9, 8), (c, 9, 8))
        self.assertEqual(C.m(c), (c, 1, 2))
        self.assertEqual(c.n(1, k=2), ((1,), {"k": 2}))

    def test_wide_arity_defaults(self):
        def f(
            a,
            b=1,
            c=2,
            d=3,
            e=4,
            f_=5,
            g=6,
            h=7,
            i=8,
            j=9,
        ):
            return (a, b, c, d, e, f_, g, h, i, j)

        self.assertEqual(f(0), (0, 1, 2, 3, 4, 5, 6, 7, 8, 9))
        self.assertEqual(f(0, 10, 20), (0, 10, 20, 3, 4, 5, 6, 7, 8, 9))
        self.assertEqual(
            f(0, 1, 2, 3, 4, 5, 6, 7, 8, 9), (0, 1, 2, 3, 4, 5, 6, 7, 8, 9)
        )

    def test_defaults_with_keyword_mixed_call(self):
        def f(a, b=1, c=2):
            return (a, b, c)

        self.assertEqual(f(0, c=9), (0, 1, 9))
        self.assertEqual(f(0, b=8, c=9), (0, 8, 9))
        with self.assertRaises(TypeError) as ctx:
            f(0, 1, b=8)
        self.assertIn("f() got multiple values for argument 'b'", str(ctx.exception))

    def test_lambda_and_comprehension_call(self):
        f = lambda a, b=2: (a, b)
        self.assertEqual(f(1), (1, 2))
        self.assertEqual([f(i) for i in range(3)], [(0, 2), (1, 2), (2, 2)])
        self.assertEqual(list(f(i, b=i) for i in range(3)), [(0, 0), (1, 1), (2, 2)])

    def test_unpacked_positional_args(self):
        def f(a, b=1, c=2):
            return (a, b, c)

        args = (7,)
        self.assertEqual(f(*args), (7, 1, 2))
        self.assertEqual(f(*args, *args), (7, 7, 2))
        self.assertEqual(f(*[1, 2, 3]), (1, 2, 3))

    def test_warmed_sites_answer_the_same(self):
        # A call site that runs enough times gets specialized, and the
        # specialized kernel is then what answers every later call. The answer
        # must not depend on that: warm the site first, then check the shapes
        # the defaults route claims, the shapes it must decline, and the error
        # cases it must still report.
        def f(a, b=1, c=2):
            return (a, b, c)

        for _ in range(4000):
            f(0)
        self.assertEqual(f(0), (0, 1, 2))
        self.assertEqual(f(0, 5), (0, 5, 2))
        self.assertEqual(f(0, c=9), (0, 1, 9))
        self.assertEqual(f(a=0, b=1, c=2), (0, 1, 2))
        with self.assertRaises(TypeError) as ctx:
            f()
        self.assertIn("f() missing 1 required positional argument: 'a'", str(ctx.exception))
        with self.assertRaises(TypeError) as ctx:
            f(1, 2, 3, 4)
        self.assertIn("but 4 were given", str(ctx.exception))
        # A mutated `__defaults__` bumps the function's version, which deoptimizes
        # the warmed site; the next calls must still bind the new tuple.
        f.__defaults__ = ("x", "y")
        self.assertEqual(f(0), (0, "x", "y"))
        self.assertEqual(f(0, "m"), (0, "m", "y"))
        f.__defaults__ = (1, 2)


    def test_warmed_cached_bound_method(self):
        class C:
            def m(self, a=1, b=2):
                return (self, a, b)

            def n(self, *args):
                return args

        c = C()
        m = c.m
        for _ in range(4000):
            m()
        self.assertEqual(m(), (c, 1, 2))
        self.assertEqual(m(9), (c, 9, 2))
        self.assertEqual(m(9, 8), (c, 9, 8))
        with self.assertRaises(TypeError) as ctx:
            m(1, 2, 3)
        self.assertIn("takes from 1 to 3 positional arguments", str(ctx.exception))
        n = c.n
        for _ in range(4000):
            n()
        self.assertEqual(n(), ())
        self.assertEqual(n(1, 2), (1, 2))


if __name__ == "__main__":
    unittest.main(verbosity=2)
