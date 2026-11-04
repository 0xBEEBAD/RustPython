"""Pin the behavior of keyword-argument binding around the fastlocals call path.

Run against CPython first, then RustPython: any difference is a fork bug, and any
difference after a call-path change is that change breaking binding.
"""

import unittest
from functools import partial


def two(a, b):
    return (a, b)


def three(a, b, c):
    return (a, b, c)


def defaults(a, b=99, c=100):
    return (a, b, c)


def posonly(a, b, /, c, d):
    return (a, b, c, d)


def kwonly(a, *, b=1, c=2):
    return (a, b, c)


def all_kwonly(*, a=1):
    return a


def strict_kwonly(x, *, y):
    return (x, y)


def posonly_and_kwonly(a, /, b, *, c):
    return (a, b, c)


def gen_kwonly(*, n=1):
    yield n


def varkw(a, **kw):
    return (a, kw, list(kw))


def varargs(a, *args, b=None):
    return (a, args, b)


def nine(a, b, c, d, e, f, g, h, i):
    return (a, b, c, d, e, f, g, h, i)


def gen(a, b=1):
    yield a
    yield b


def cell_holder(a, b=2):
    def inner():
        return (a, b)

    return inner


def self_defaulting(a=[0]):
    a.append(1)
    return a


class Klass:
    def method(self, a, b=2):
        return (self, a, b)

    def __init__(self, a, b=3):
        self.a = a
        self.b = b


def recursive(n, acc=0):
    if n == 0:
        return acc
    return recursive(n - 1, acc=acc + n)


def msg_of(fn, *args, **kwargs):
    """The TypeError message a call produces, or None if it succeeds."""
    try:
        fn(*args, **kwargs)
    except TypeError as exc:
        return str(exc)
    return None


class KeywordBindingTests(unittest.TestCase):
    def test_exact_fill_in_every_spelling(self):
        self.assertEqual(two(1, 2), (1, 2))
        self.assertEqual(two(1, b=2), (1, 2))
        self.assertEqual(two(a=1, b=2), (1, 2))
        self.assertEqual(two(b=2, a=1), (1, 2))
        self.assertEqual(two(**{"a": 1, "b": 2}), (1, 2))
        self.assertEqual(three(1, c=3, b=2), (1, 2, 3))
        self.assertEqual(three(b=2, a=1, c=3), (1, 2, 3))

    def test_defaults_only_when_the_call_leaves_a_parameter_out(self):
        self.assertEqual(defaults(1), (1, 99, 100))
        self.assertEqual(defaults(1, 2), (1, 2, 100))
        self.assertEqual(defaults(1, c=3), (1, 99, 3))
        self.assertEqual(defaults(1, b=2, c=3), (1, 2, 3))
        self.assertEqual(defaults(1, c=3, b=2), (1, 2, 3))
        self.assertEqual(defaults(a=1, b=2, c=3), (1, 2, 3))
        self.assertEqual(defaults(c=3, b=2, a=1), (1, 2, 3))

    def test_mutable_default_is_shared_across_calls(self):
        self.assertEqual(self_defaulting(), [0, 1])

    def test_positional_only_still_decides(self):
        self.assertEqual(posonly(1, 2, c=3, d=4), (1, 2, 3, 4))
        self.assertEqual(posonly(1, 2, 3, d=4), (1, 2, 3, 4))
        self.assertEqual(
            msg_of(posonly, 1, 2, 3, a=4),
            "posonly() got some positional-only arguments passed as keyword arguments: 'a'",
        )
        # A keyword that collides with a positional value is reported as
        # "multiple values" when it comes first in call order, and a
        # positional-only keyword reported first wins the whole error: CPython
        # scans the positional-only parameters in order and names every
        # collision it finds.
        self.assertEqual(msg_of(posonly, 1, 2, 3, c=4, b=5), "posonly() got multiple values for argument 'c'")
        self.assertEqual(
            msg_of(posonly, 1, 2, 3, b=5, c=4),
            "posonly() got some positional-only arguments passed as keyword arguments: 'b'",
        )
        self.assertEqual(msg_of(posonly, 1, 2, 3, d=4, c=5), "posonly() got multiple values for argument 'c'")
        self.assertEqual(
            msg_of(posonly, 1, 2, 3, b=5, a=4),
            "posonly() got some positional-only arguments passed as keyword arguments: 'a, b'",
        )

    def test_keyword_only_never_binds_positionally(self):
        self.assertEqual(kwonly(1), (1, 1, 2))
        self.assertEqual(kwonly(1, b=5), (1, 5, 2))
        self.assertEqual(kwonly(1, c=5, b=4), (1, 4, 5))
        self.assertEqual(kwonly(a=1), (1, 1, 2))
        self.assertEqual(msg_of(kwonly, 1, 2), "kwonly() takes 1 positional argument but 2 were given")
        self.assertEqual(all_kwonly(), 1)
        self.assertEqual(all_kwonly(a=7), 7)
        self.assertEqual(msg_of(all_kwonly, 7), "all_kwonly() takes 0 positional arguments but 1 was given")

    def test_varkw_keeps_call_order(self):
        a, kw, order = varkw(1, z=1, y=2)
        self.assertEqual((a, kw), (1, {"z": 1, "y": 2}))
        self.assertEqual(order, ["z", "y"])
        self.assertEqual(varkw(a=1)[0], 1)
        self.assertEqual(varkw(1, **{"z": 1, "y": 2})[2], ["z", "y"])

    def test_varargs_and_keyword_only_combine(self):
        self.assertEqual(varargs(1), (1, (), None))
        self.assertEqual(varargs(1, 2, 3), (1, (2, 3), None))
        self.assertEqual(varargs(1, 2, b=3), (1, (2,), 3))
        self.assertEqual(varargs(1, b=3), (1, (), 3))
        self.assertEqual(varargs(a=1, b=3), (1, (), 3))

    def test_unexpected_keyword_message_and_suggestion(self):
        self.assertEqual(msg_of(two, 1, c=3), "two() got an unexpected keyword argument 'c'")
        self.assertEqual(msg_of(three, alphabet=1), "three() got an unexpected keyword argument 'alphabet'")

    def test_multiple_values_comes_from_unpacking(self):
        spread = {"a": 1, "b": 2}
        self.assertEqual(msg_of(two, 1, **spread), "two() got multiple values for argument 'a'")
        self.assertEqual(msg_of(two, 1, 2, **spread), "two() got multiple values for argument 'a'")

    def test_nonstring_keyword_is_rejected_before_binding(self):
        # A non-string key is rejected where the call is spelled, so it has to
        # be expanded inside the try -- passing it through a helper's own
        # keywords raises there instead.
        def attempt(spread):
            try:
                two(**spread)
            except TypeError as exc:
                return str(exc)
            return None

        self.assertEqual(attempt({1: 2}), "keywords must be strings")
        self.assertEqual(attempt({"a": 1, 2: 3}), "keywords must be strings")
        self.assertEqual(attempt({"a": 1, "b": 2}), None)

    def test_str_subclass_keyword_binds_by_content(self):
        class S(str):
            pass

        keys = {S("a"): 1, "b": 2}
        self.assertEqual(two(**keys), (1, 2))

    def test_more_arguments_than_the_fast_path_stages(self):
        kwargs = {n: i for i, n in enumerate("abcdefghi", 1)}
        self.assertEqual(nine(**kwargs), (1, 2, 3, 4, 5, 6, 7, 8, 9))
        self.assertEqual(nine(1, 2, 3, 4, 5, 6, g=7, h=8, i=9), (1, 2, 3, 4, 5, 6, 7, 8, 9))
        self.assertEqual(msg_of(nine, 1, 2, 3, 4, 5, 6, 7, 8, 9, i=10), "nine() got multiple values for argument 'i'")

    def test_keyword_only_parameters_bind_by_name(self):
        self.assertEqual(strict_kwonly(1, y=2), (1, 2))
        self.assertEqual(strict_kwonly(x=1, y=2), (1, 2))
        self.assertEqual(strict_kwonly(y=2, x=1), (1, 2))
        self.assertEqual(
            msg_of(strict_kwonly, 1),
            "strict_kwonly() missing 1 required keyword-only argument: 'y'",
        )
        self.assertEqual(posonly_and_kwonly(1, 2, c=3), (1, 2, 3))
        self.assertEqual(posonly_and_kwonly(1, b=2, c=3), (1, 2, 3))
        self.assertEqual(
            msg_of(posonly_and_kwonly, 1, 2, 3),
            "posonly_and_kwonly() takes 2 positional arguments but 3 were given",
        )
        self.assertEqual(
            msg_of(posonly_and_kwonly, 1, c=3, a=4),
            "posonly_and_kwonly() got some positional-only arguments passed as keyword arguments: 'a'",
        )

    def test_generator_call_with_keyword(self):
        self.assertEqual(list(gen(1, b=7)), [1, 7])
        self.assertEqual(list(gen(a=1, b=7)), [1, 7])
        self.assertEqual(list(gen(a=1)), [1, 1])
        self.assertEqual(list(gen_kwonly(n=2)), [2])
        self.assertEqual(list(gen_kwonly()), [1])

    def test_captured_parameters_keep_their_cells(self):
        self.assertEqual(cell_holder(1, b=3)(), (1, 3))
        self.assertEqual(cell_holder(a=1, b=3)(), (1, 3))
        self.assertEqual(cell_holder(b=3, a=1)(), (1, 3))
        self.assertEqual(cell_holder(1)(), (1, 2))

    def test_bound_method_with_keyword(self):
        obj = Klass(1, b=9)
        self.assertEqual((obj.a, obj.b), (1, 9))
        self.assertEqual(Klass(a=1, b=9).b, 9)
        self.assertEqual(obj.method(1, b=9)[1:], (1, 9))
        self.assertEqual(obj.method(a=1, b=9)[1:], (1, 9))
        self.assertEqual(obj.method(b=9, a=1)[1:], (1, 9))
        self.assertEqual(obj.method(1)[1:], (1, 2))

    def test_recursion_and_partial_through_the_same_shape(self):
        self.assertEqual(recursive(4), 10)
        self.assertEqual(recursive(4, acc=100), 110)
        self.assertEqual(recursive(n=4), 10)
        add_two = partial(two, 1)
        self.assertEqual(add_two(b=2), (1, 2))
        both = partial(two, b=2)
        self.assertEqual(both(a=1), (1, 2))

    def test_missing_argument_still_reported(self):
        self.assertEqual(msg_of(two, 1), "two() missing 1 required positional argument: 'b'")
        self.assertEqual(msg_of(two, a=1), "two() missing 1 required positional argument: 'b'")
        self.assertEqual(msg_of(three, a=1, b=2), "three() missing 1 required positional argument: 'c'")


if __name__ == "__main__":
    unittest.main(verbosity=2)
