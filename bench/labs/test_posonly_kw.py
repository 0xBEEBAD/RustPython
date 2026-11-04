"""Positional-only / unexpected-keyword TypeError parity (CPython ceval.c).

CPython's `positional_only_passed_as_keyword` is called from the keyword loop
only when the function has no ``**kwargs``, and it scans *every* keyword, so a
positional-only collision outranks "unexpected keyword argument" whatever the
call order. The names in the message follow parameter order, not call order.

The sample callables live at module scope because CPython prefixes the message
with the function qualname, which for a nested def would include the test name.

Run: <exe> bench/labs/test_posonly_kw.py
"""

import sys
import unittest


def plain(a, b, /):
    return (a, b)


def names(a, b, /):
    return (a, b)


def mixed(a, b, /, c, d=4):
    return (a, b, c, d)


def varkw(a, b, /, **kw):
    return kw


def posdefault(a=1, /, b=2):
    return (a, b)


def kwonly(a, /, *, b=2):
    return (a, b)


def spelled(alpha, beta):
    return (alpha, beta)


def sink(a, b, /, c=None):
    return c


def raises(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except TypeError as exc:
        return str(exc)
    except Exception as exc:  # pragma: no cover - wrong exception type
        return f"{type(exc).__name__}: {exc}"
    return None


def raises_kwargs(fn, args, kwargs):
    """Same as raises(), but the keywords reach the call through ** expansion
    of a dict that is not literal, so non-str keys survive."""
    try:
        fn(*args, **kwargs)
    except TypeError as exc:
        return str(exc)
    return None


class PosonlyKeywordTest(unittest.TestCase):
    def test_collision_reported(self):
        self.assertEqual(
            raises(plain, a=1),
            "plain() got some positional-only arguments passed as keyword arguments: 'a'",
        )

    def test_names_follow_parameter_order(self):
        # The call spells b first; CPython still lists 'a, b'.
        self.assertEqual(
            raises(names, **{"b": 1, "a": 2}),
            "names() got some positional-only arguments passed as keyword arguments: 'a, b'",
        )

    def test_collision_outranks_unknown_keyword(self):
        for kwargs in ({"a": 1, "zz": 2}, {"zz": 2, "a": 1}):
            with self.subTest(kwargs=tuple(kwargs)):
                self.assertEqual(
                    raises(plain, **kwargs),
                    "plain() got some positional-only arguments "
                    "passed as keyword arguments: 'a'",
                )

    def test_collision_with_bound_positional(self):
        self.assertEqual(
            raises(mixed, 1, a=2),
            "mixed() got some positional-only arguments passed as keyword arguments: 'a'",
        )
        self.assertEqual(
            raises(mixed, 1, 2, c=3, b=4),
            "mixed() got some positional-only arguments passed as keyword arguments: 'b'",
        )

    def test_kwargs_absorbs_the_name(self):
        # No collision error at all: the keyword lands in **kw, and the arity
        # error is the one for the missing positional.
        self.assertEqual(
            raises(varkw, 1, a=2), "varkw() missing 1 required positional argument: 'b'"
        )
        self.assertEqual(varkw(1, 2, zz=3), {"zz": 3})

    def test_defaulted_posonly_and_kwonly(self):
        self.assertEqual(
            raises(posdefault, a=5),
            "posdefault() got some positional-only arguments passed as keyword arguments: 'a'",
        )
        self.assertEqual(
            raises(kwonly, 1, a=2),
            "kwonly() got some positional-only arguments passed as keyword arguments: 'a'",
        )

    def test_suggestion_is_not_gated_on_keyword_count(self):
        self.assertEqual(
            raises(spelled, alph=1),
            "spelled() got an unexpected keyword argument 'alph'. Did you mean 'alpha'?",
        )
        # CPython computes the suggestion for the first keyword it cannot
        # match, even when a second unexpected keyword follows it.
        self.assertEqual(
            raises(spelled, alph=1, btay=2),
            "spelled() got an unexpected keyword argument 'alph'. Did you mean 'alpha'?",
        )

    def test_no_suggestion_for_posonly_only_function(self):
        self.assertEqual(
            raises(plain, al=1, bb=2), "plain() got an unexpected keyword argument 'al'"
        )

    def test_non_str_keyword(self):
        self.assertEqual(raises_kwargs(plain, (), {1: 2}), "keywords must be strings")

    def test_unrelated_messages_unchanged(self):
        self.assertEqual(
            raises(plain, 1, 2, 3),
            "plain() takes 2 positional arguments but 3 were given",
        )
        self.assertEqual(
            raises(mixed, 1, 2, e=3), "mixed() got an unexpected keyword argument 'e'"
        )

    def test_call_order_does_not_choose_the_error(self):
        # 'b' is positional-only; the keywords arrive in the order zz, b.
        self.assertEqual(
            raises(sink, 1, zz=0, b=2),
            "sink() got some positional-only arguments passed as keyword arguments: 'b'",
        )


if __name__ == "__main__":
    print("==", sys.version.split()[0], sys.implementation.name)
    unittest.main(verbosity=2)
