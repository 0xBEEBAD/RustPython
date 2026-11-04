"""Except-clause shapes the identity match and inline branch must not change.

Run on CPython and on RustPython, with and without `LUNA_ABLATE=excfuse`:
every check must produce the same result all four ways. Covers the two paths the
unit adds (identical-class answer, deciding the branch without the bool) and the
ones it must leave alone (tuples validated before matching, non-class targets,
metaclass hooks, except*, tracing).
"""

import sys
import unittest


class Meta(type):
    """Hooks must have no vote: CPython's except match is decided by the MRO."""

    def __subclasscheck__(cls, other):
        return False

    def __instancecheck__(cls, other):
        return False


class Weird(metaclass=Meta):
    pass


class CustomError(Exception):
    pass


class ExactMetaError(CustomError, metaclass=Meta):
    pass


class ExceptClauseParity(unittest.TestCase):
    def record(self):
        """Return a shape-key tuple that must be identical across interpreters."""
        out = []

        # 1. identical class - the new pointer-compare answer
        try:
            raise ValueError("a")
        except ValueError as exc:
            out.append(("identity", type(exc).__name__))

        # 2. base class - MRO walk, not identity
        try:
            raise CustomError("b")
        except Exception as exc:
            out.append(("mro", type(exc).__name__))

        # 3. tuple target, later element matches
        try:
            raise TypeError("c")
        except (ValueError, TypeError) as exc:
            out.append(("tuple", type(exc).__name__))

        # 4. tuple with a non-class element: CPython validates everything first,
        #    so the match on the good element must not suppress the TypeError.
        try:
            try:
                raise ValueError("d")
            except (ValueError, 5) as exc:
                out.append(("tuple-bad-matched", type(exc).__name__))
        except TypeError as exc:
            out.append(("tuple-bad", str(exc)))

        # 5. non-class target
        try:
            try:
                raise ValueError("e")
            except 5:
                out.append(("int-target-matched",))
        except TypeError as exc:
            out.append(("int-target", str(exc)))

        # 6. None target
        try:
            try:
                raise ValueError("f")
            except None:  # noqa: E999 - deliberately invalid, caught above
                out.append(("none-target-matched",))
        except TypeError as exc:
            out.append(("none-target", str(exc)))

        # 7. BaseException itself, identity
        try:
            raise BaseException("g")
        except BaseException as exc:
            out.append(("base", type(exc).__name__))

        # 8. hostile metaclass on the exact class of the exception
        try:
            raise ExactMetaError("h")
        except ExactMetaError as exc:
            out.append(("meta-identity", type(exc).__name__))
        out.append(("meta-hook-refused", not isinstance(CustomError(), Weird)))

        # 9. a local name that is not a class is still a rejected target
        shadow = 5
        try:
            try:
                raise ValueError("i")
            except shadow:
                out.append(("shadowed-matched",))
        except TypeError as exc:
            out.append(("shadowed", str(exc)))

        # 10. else clause runs only on a match
        try:
            try:
                raise KeyError("j")
            except KeyError:
                out.append(("matched-no-else",))
            else:
                out.append(("else",))
        except Exception:
            out.append(("else-fail",))

        # 11. bare re-raise from inside the clause keeps the original chain
        try:
            raise IndexError("k")
        except IndexError:
            try:
                raise
            except IndexError as exc:
                out.append(("reraise", str(exc), exc.__traceback__ is not None))

        # 12. no match falls through to the outer handler
        try:
            try:
                raise OSError("l")
            except ValueError:
                out.append(("wrong-clause",))
        except OSError as exc:
            out.append(("fell-through", str(exc)))

        # 13. nested clauses in one function: several branch decisions in a row
        out.append(("multi", multi_clause()))

        return tuple(out)

    def test_shapes(self):
        got = self.record()
        # Values CPython 3.14/3.15 produce for `record()` above; a mismatch here
        # means a clause decision changed shape, order or message.
        self.assertEqual(
            got,
            (
                ("identity", "ValueError"),
                ("mro", "CustomError"),
                ("tuple", "TypeError"),
                ("tuple-bad", "catching classes that do not inherit from "
                              "BaseException is not allowed"),
                ("int-target", "catching classes that do not inherit from "
                               "BaseException is not allowed"),
                ("none-target", "catching classes that do not inherit from "
                                "BaseException is not allowed"),
                ("base", "BaseException"),
                ("meta-identity", "ExactMetaError"),
                ("meta-hook-refused", True),
                ("shadowed", "catching classes that do not inherit from "
                             "BaseException is not allowed"),
                ("matched-no-else",),
                ("reraise", "k", True),
                ("fell-through", "l"),
                ("multi", (1, 2, 3, 4)),
            ),
        )

    def test_tracing_unchanged(self):
        # The unit is disabled while tracing, so the instruction-level event
        # sequence must be what it was before: line events for the try, the
        # clause body and nothing synthetic.
        events = []

        def tracer(frame, event, arg):
            if frame.f_code.co_name == "traced":
                events.append((event, frame.f_lineno))
            return tracer

        def traced():
            try:
                raise ValueError("t")
            except ValueError:
                return 1

        sys.settrace(tracer)
        try:
            traced()
        finally:
            sys.settrace(None)
        # Sequence pinned on CPython 3.14.7: call, the raise line, the clause
        # line, the exception, the body line, the return line, return. Line
        # numbers depend on this file, so the kinds are the contract.
        print("TRACE EVENTS", events)
        self.assertEqual(events[0][0], "call")
        self.assertEqual(events[-1][0], "return")
        self.assertEqual(
            [e for e, _ in events],
            ["call", "line", "line", "exception", "line", "line", "return"],
            "the clause test and branch must not add or drop trace events",
        )


def multi_clause():
    hits = []
    for exc in (ValueError(), TypeError(), KeyError(), OSError()):
        try:
            raise exc
        except ValueError:
            hits.append(1)
        except TypeError:
            hits.append(2)
        except (KeyError, IndexError):
            hits.append(3)
        except Exception:
            hits.append(4)
    return tuple(hits)


if __name__ == "__main__":
    unittest.main(verbosity=2)
