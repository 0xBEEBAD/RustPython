"""Behaviour guards for reusing the `for i in range(n)` loop variable.

The interpreter wants to keep one int object alive for a range loop and add the
step to it in place, which is only legal while nobody else can see the object.
These tests pin what a Python program may observe, so a wrong reuse - mutating
an object the program still holds - fails here rather than in the field.

Every expectation is CPython 3.14 behaviour; run this file on
`bench/labs/cp314/python.exe` first and require the same result.
"""
import sys
import threading
import unittest


class RangeIntReuseTest(unittest.TestCase):
    def test_loop_values_kept_alive_are_correct_and_distinct(self):
        vals = []
        for i in range(1000, 1200):
            vals.append(i)
        self.assertEqual(vals, list(range(1000, 1200)))
        self.assertEqual(len({id(v) for v in vals}), 200, "alive ints share an id")

    def test_rebound_loop_variable_does_not_mutate_the_held_object(self):
        held = []
        for i in range(1000, 1020):
            held.append(i)
            i = -1  # the slot now holds a different object
        self.assertEqual(held, list(range(1000, 1020)))
        self.assertEqual([type(v) for v in held], [int] * 20)
        self.assertEqual(len({id(v) for v in held}), 20)

    def test_negative_step_and_wide_step(self):
        self.assertEqual(
            [i for i in range(3000, 2900, -7)], list(range(3000, 2900, -7))
        )
        self.assertEqual(
            [i for i in range(1000, 5000, 999)], list(range(1000, 5000, 999))
        )

    def test_values_beyond_one_limb(self):
        base = 2**63
        got = [i for i in range(base, base + 8)]
        self.assertEqual(got, list(range(base, base + 8)))
        big = 10**30
        self.assertEqual([i for i in range(big, big + 3)], [big, big + 1, big + 2])

    def test_small_int_cache_is_not_corrupted(self):
        pool = list(range(-5, 257))
        self.assertEqual(pool, list(range(-5, 257)))
        for _ in range(3000):
            pass
        for i in range(1000, 2000):
            pass
        self.assertEqual(pool, list(range(-5, 257)))
        self.assertEqual(2 + 2, 4)
        self.assertIs(pool[0], -5)

    def test_ints_used_as_dict_keys_stay_valid(self):
        d = {}
        for i in range(1000, 1100):
            d[i] = 2 * i
        self.assertEqual(len(d), 100)
        self.assertEqual(sorted(d), list(range(1000, 1100)))
        self.assertEqual([d[i] for i in range(1000, 1100)], [2 * i for i in range(1000, 1100)])

    def test_int_escaped_through_an_exception_keeps_its_value(self):
        held = []
        for i in range(1000, 1050):
            try:
                raise ValueError(i)
            except ValueError as e:
                self.assertEqual(e.args[0], i)
                held.append(e.args[0])
        self.assertEqual(held, list(range(1000, 1050)))

    def test_generator_frame_keeps_loop_values(self):
        def gen():
            for i in range(1000, 1030):
                yield i

        self.assertEqual(list(gen()), list(range(1000, 1030)))

    def test_nested_range_loops(self):
        seen = []
        for i in range(1000, 1005):
            for j in range(1000, 1005):
                seen.append((i, j))
        self.assertEqual(len(seen), 25)
        self.assertEqual(seen[0], (1000, 1000))
        self.assertEqual(seen[-1], (1004, 1004))
        self.assertEqual(len({(a, b) for a, b in seen}), 25)

    def test_loops_are_correct_with_a_live_second_thread(self):
        stop = threading.Event()
        worker = threading.Thread(target=stop.wait, daemon=True)
        worker.start()
        try:
            self.assertEqual(
                [i for i in range(1000, 1100)], list(range(1000, 1100))
            )
            vals = []
            for i in range(2000, 2050):
                vals.append(i)
            self.assertEqual(vals, list(range(2000, 2050)))
        finally:
            stop.set()
            worker.join()

    def test_separate_iterators_do_not_share_state(self):
        a = iter(range(1000, 1010))
        b = iter(range(2000, 2010))
        self.assertEqual([next(a), next(b), next(a), next(b)], [1000, 2000, 1001, 2001])
        self.assertEqual(list(a), list(range(1002, 1010)))
        self.assertEqual(list(b), list(range(2002, 2010)))

    def test_loop_variable_survives_into_a_closure(self):
        fns = []
        for i in range(1000, 1005):
            fns.append(lambda i=i: i)
        self.assertEqual([f() for f in fns], list(range(1000, 1005)))

    def test_id_reuse_while_alive_is_impossible(self):
        # Two loop ints from the *same* iteration must be the same object
        # (LOAD_FAST twice) and a live one must never be handed out again.
        keep = []
        for i in range(1000, 1010):
            self.assertIs(i, i)
            keep.append(i)
        self.assertEqual(keep, list(range(1000, 1010)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
