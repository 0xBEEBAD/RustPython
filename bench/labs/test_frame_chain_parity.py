"""Exited-frame f_back retention, pinned against CPython.

The fork materializes frames lazily: a running frame lives on the datastack and
only grows a FrameObject when something observes it. When that observation
happens deep in a call chain and the ancestors then return, CPython keeps the
whole chain walkable (a frame holds a strong reference to its caller), so
`f_back`, `traceback.extract_stack(frame)` and `exc.__traceback__.tb_frame`
still see every ancestor. This file pins that observable chain, which is what
test_traceback.LimitTests.test_extract_stack and test_sys.test_current_exceptions
depend on.

Run on CPython 3.14.7 (all green) and on RustPython (red until each snapshot is
completed as its own frame unwinds).
"""
import sys
import unittest
import traceback


def returns_frame(depth):
    """Return the innermost frame after every ancestor has already returned."""
    if depth == 0:
        return sys._getframe()
    frame = returns_frame(depth - 1)
    return frame


def names_of_chain(frame):
    names = []
    while frame is not None:
        names.append(frame.f_code.co_name)
        frame = frame.f_back
    return names


class ChainAfterReturn(unittest.TestCase):
    def test_deep_chain_survives_returns(self):
        frame = returns_frame(4)
        names = names_of_chain(frame)
        self.assertEqual(
            [n for n in names if n == "returns_frame"],
            ["returns_frame"] * 5,
            "every returns_frame level must stay walkable: %r" % (names,),
        )

    def test_chain_reaches_the_test_frame(self):
        frame = returns_frame(3)
        names = names_of_chain(frame)
        self.assertIn("test_chain_reaches_the_test_frame", names)
        self.assertIn("<module>", names[-1])

    def test_repeated_walk_is_stable(self):
        frame = returns_frame(3)
        self.assertIs(frame.f_back, frame.f_back)
        self.assertEqual(names_of_chain(frame), names_of_chain(frame))

    def test_extract_stack_on_returned_frame(self):
        frame = returns_frame(4)
        entries = traceback.extract_stack(frame)
        self.assertGreater(len(entries), 5, "extract_stack lost ancestors")
        self.assertEqual(entries[-1].name, "returns_frame")

    def test_format_stack_uses_the_chain(self):
        frame = returns_frame(2)
        entries = traceback.extract_stack(frame)
        self.assertEqual([e.name for e in entries].count("returns_frame"), 3)
        text = "".join(traceback.format_stack(frame))
        self.assertEqual(text.count("in returns_frame"), 3, text)

    def test_traceback_frames_survive_propagation(self):
        # The exception propagated out of every raise_inner level, so those
        # frames have all returned by the time the handler looks at them.
        try:
            raise_inner(3)
        except ValueError as exc:
            tb = exc.__traceback__
            while tb.tb_next:
                tb = tb.tb_next
            names = names_of_chain(tb.tb_frame)
            self.assertIn(
                "raise_inner",
                names,
                "deepest traceback frame lost its callers: %r" % (names,),
            )
        else:
            self.fail("expected ValueError")


def raise_inner(depth):
    if depth == 0:
        raise ValueError("inner")
    raise_inner(depth - 1)


class GeneratorChain(unittest.TestCase):
    def test_suspended_generator_chain(self):
        # CPython gives a suspended generator frame no f_back at all: the
        # resuming caller is not part of the generator's own chain.
        def gen():
            yield sys._getframe()

        g = gen()
        frame = next(g)
        self.assertEqual(names_of_chain(frame), ["gen"])
        g.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
