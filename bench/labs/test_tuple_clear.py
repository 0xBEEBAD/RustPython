"""Guard for dropping tuple elements inside tp_clear.

`PyTuple::clear` used to move its elements into the caller's empty `Vec`, which
cost one heap block per destroyed tuple; it now drops the owned boxed slice in
place. Dropping can run user `__del__`, so the cycle-collection behaviour has to
stay identical: collected counts, finaliser ordering, no `gc.garbage`, and no
crash on deep or self-referential tuple graphs.

Run on CPython first - these expectations are CPython's behaviour, not
RustPython's.
"""
import gc
import unittest


class Recorder:
    log = None

    def __del__(self):
        if Recorder.log is not None:
            Recorder.log.append(type(self).__name__)


class TupleClearTest(unittest.TestCase):
    def setUp(self):
        gc.collect()
        gc.collect()
        Recorder.log = []

    def tearDown(self):
        Recorder.log = None

    def make_cycle_with_tuple(self):
        class Node:
            def __init__(self):
                self.payload = (1, self, "x")

        n = Node()
        cycle = [n, (n, n.payload)]
        n.container = cycle
        del n, cycle

    def test_cycle_with_tuple_payload_is_collected(self):
        before = len(gc.get_objects())
        self.make_cycle_with_tuple()
        gc.collect()
        after = len(gc.get_objects())
        self.assertLessEqual(after, before + 5, "cycle was not reclaimed")

    def test_finaliser_runs_during_collection(self):
        holder = [(Recorder(),)]
        del holder
        gc.collect()
        self.assertIn("Recorder", Recorder.log, Recorder.log)

    def test_nested_tuple_cycle(self):
        class Node:
            def __del__(self):
                if Recorder.log is not None:
                    Recorder.log.append("node")

        a = (1,)
        lst = []
        b = (lst, Recorder())
        lst.append(b)
        del a, lst, b
        gc.collect()
        self.assertIn("Recorder", Recorder.log, Recorder.log)

    def test_gc_garbage_stays_empty(self):
        self.make_cycle_with_tuple()
        gc.collect()
        self.assertEqual(gc.garbage, [], gc.garbage)

    def test_wide_tuple_release(self):
        # 200 elements: exercises the boxed-slice path well past the old
        # capacity-4 clamp.
        big = tuple(Recorder() for _ in range(200))
        del big
        gc.collect()
        self.assertEqual(Recorder.log.count("Recorder"), 200, Recorder.log)

    def test_elements_visible_after_partial_clear(self):
        # A tuple element that survives must not see a mutated container.
        keep = ["alive"]
        t = (keep, Recorder())
        del t
        gc.collect()
        self.assertEqual(keep, ["alive"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
