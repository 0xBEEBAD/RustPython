"""Red test: `for i in range(n)` must not allocate one block per iteration.

Uses the opt-in counters from `--features alloc-stats` (`sys._alloc_stats`), so
this file only asserts something on an instrumented build and skips cleanly on
CPython.  The shape is the loop floor every benchmark case wraps its body in:
values past the immortal -5..256 pool currently cost one fresh int per
iteration, while CPython pays ~4 ns because its ints carry their digits inline
and come from a per-thread freelist.

Gross allocations are what matters here: an alloc/free *pair* per iteration is
exactly the cost being removed, so a "net zero" reading would prove nothing.
"""
import sys
import unittest

HAS_STATS = hasattr(sys, "_alloc_stats")
N = 100_000


def gross_per_op(fn, n=N):
    """Gross allocations per iteration of `fn`, after a warm-up run."""
    fn()  # warm the code path and the type caches
    sys._alloc_stats(True)
    fn()
    stats = sys._alloc_stats(False)
    return stats["allocs"] / n


@unittest.skipUnless(HAS_STATS, "needs a --features alloc-stats build")
class RangeIntAllocTest(unittest.TestCase):
    def test_plain_range_loop_allocates_nothing(self):
        def loop():
            for i in range(300, 300 + N):
                pass

        per_op = gross_per_op(loop)
        self.assertLess(
            per_op,
            0.05,
            f"the range loop still allocates {per_op:.3f} blocks per iteration",
        )

    def test_pooled_range_loop_allocates_nothing(self):
        def loop():
            for i in range(200):
                pass

        per_op = gross_per_op(loop)
        self.assertLess(per_op, 0.02, f"pooled loop allocates {per_op:.3f}/iter")

    def test_kept_alive_loop_values_still_allocate(self):
        # The fallback has to stay: a body that retains every value forces a
        # fresh object each time, so keeping the values must still cost about one
        # block per iteration *more* than dropping them on the floor.  Only a
        # lower bound is asserted - an upper one would pin today's dict
        # internals rather than behaviour - and the keys are checked, because a
        # reuse that silently lost values would show up here.
        def drop():
            for i in range(300, 300 + N):
                pass

        def keep():
            d = {}
            for i in range(300, 300 + N):
                d[i] = 1
            return d

        expected = dict.fromkeys(range(300, 300 + N), 1)
        self.assertEqual(keep(), expected, "loop keys are wrong")
        delta = gross_per_op(keep) - gross_per_op(drop)
        self.assertGreater(delta, 0.8, f"retained loop ints cost only {delta:.3f}/iter")

    def test_enumerate_over_range_allocates_nothing_extra(self):
        def loop():
            for _ in enumerate(range(300, 300 + N)):
                pass

        per_op = gross_per_op(loop)
        self.assertLess(per_op, 2.5, f"enumerate loop allocates {per_op:.3f}/iter")


if __name__ == "__main__":
    print("alloc counters available:", HAS_STATS)
    unittest.main(verbosity=2)
