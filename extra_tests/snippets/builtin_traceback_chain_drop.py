"""A long __traceback__ chain must be freed without growing the native stack.

Each `raise` on the same exception object appends one traceback link, so N raises
make an N-link chain. Dropping it recursed through `tb_next` and overflowed the
stack once the trashcan could not cover it: the collector untracks an object it
has judged dead before freeing it, and the trashcan engages only for tracked
objects. CPython releases the same chain inside its own trashcan at any depth.
"""

import gc
import unittest

LINKS = 50_000


def build_chain(n):
    exc = ValueError("boom")
    for _ in range(n):
        try:
            raise exc
        except ValueError:
            pass
    return exc


def chain_length(exc):
    return tb_length(exc.__traceback__)


def tb_length(tb):
    length = 0
    while tb is not None:
        length += 1
        tb = tb.tb_next
    return length


class TracebackChainDropTest(unittest.TestCase):
    def test_collected_chain_frees(self):
        exc = build_chain(LINKS)
        self.assertEqual(chain_length(exc), LINKS)

        # Reaching the collector means reaching the drop path untracked, which is
        # what used to recurse.
        holder = []
        holder.append(holder)
        holder.append(exc)
        del exc
        gc.collect()

    def test_shared_tail_is_not_flattened(self):
        exc = build_chain(3)
        holder = exc.__traceback__.tb_next
        del exc
        gc.collect()
        # The head was dropped while a link further down was still referenced, so
        # that link's own tail must have survived.
        self.assertEqual(tb_length(holder), 2)


if __name__ == "__main__":
    unittest.main()
