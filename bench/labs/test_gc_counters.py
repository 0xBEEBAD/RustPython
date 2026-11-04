"""Behavioral parity test for the GC allocation counters and frame publication.

Run on both interpreters; every line must be PASS on each. This is the fast
regression gate for changes to GC track/untrack bookkeeping.

  python test_gc_counters.py
  rustpython test_gc_counters.py
"""
import gc
import sys
import weakref

failures = 0


def check(name, cond, detail=""):
    global failures
    if cond:
        print(f"PASS {name}")
    else:
        failures += 1
        print(f"FAIL {name} {detail}")


# 1. Untracked objects (ints) must not move the tracked-allocation counter.
gc.collect()
base = gc.get_count()[0]
ints = [i + 1000 for i in range(5000)]
after_ints = gc.get_count()[0]
check("ints are not gc-tracked", after_ints - base < 500, f"{base}->{after_ints}")
del ints

# 2. Tracked containers raise the counter, freeing them lowers it again.
#    Automatic collection is disabled so the counter is not reset mid-way.
gc.collect()
gc.disable()
base = gc.get_count()[0]
lists = [[i] for i in range(2000)]
after_alloc = gc.get_count()[0]
check("tracked allocs raise counter", after_alloc - base >= 1500, f"{base}->{after_alloc}")
del lists
after_free = gc.get_count()[0]
check("tracked frees lower counter", after_free - base < 200, f"{base}->{after_free}")
gc.enable()

# 3. gc.collect() zeroes the collected generation counters.
gc.collect()
check("collect zeroes gen0", gc.get_count()[0] == 0, str(gc.get_count()))

# 4. Reference cycles are still collected (bookkeeping change must not
#    lose objects from the lists).


class Node:
    def __init__(self):
        self.next = None


gc.collect()
alive = weakref.ref(Node())
n1 = Node()
n2 = Node()
n1.next = n2
n2.next = n1
w = weakref.ref(n1)
del n1, n2
collected = gc.collect()
check("cycle collected", w() is None, f"collected={collected}")

# 5. Objects with finalizers still run __del__ exactly once.
runs = []


class Finalized:
    def __del__(self):
        runs.append(1)


f = Finalized()
f.cycle = f
del f
gc.collect()
check("__del__ ran once", len(runs) == 1, str(runs))

# 6. gc.get_count() is non-negative after heavy churn (saturating Rule D).
gc.collect()
for _ in range(50):
    tmp = [([], {}, set()) for _ in range(10)]
    del tmp
counts = gc.get_count()
check("counters non-negative", all(c >= 0 for c in counts), str(counts))

# 7. Frame publication: the running frame is visible to sys._current_frames().
def inner():
    return sys._current_frames()[current_tid]


current_tid = None


def outer():
    global current_tid
    import threading
    current_tid = threading.get_ident()
    return inner()


frame = outer()
check("current frame published", frame is not None and frame.f_code.co_name == "inner")

# 8. f_back chain from a materialized frame.
def f_back_probe():
    fr = sys._getframe()
    return fr.f_back


fr = f_back_probe()
check("f_back chain", fr is not None)

print("RESULT", "FAIL" if failures else "OK")
sys.exit(1 if failures else 0)
