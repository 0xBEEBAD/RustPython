import sys, time
N = 200_000
REPS = 7

def throw(i):
    raise ValueError(i)

def loop_construct():
    for i in range(N):
        try:
            ValueError(i)
        except Exception:
            pass

def loop_raise_prebuilt():
    exc = ValueError(1)
    for i in range(N):
        try:
            raise exc
        except ValueError:
            pass

def loop_raise_new():
    for i in range(N):
        try:
            throw(i)
        except ValueError:
            pass

def loop_catch_only():
    for i in range(N):
        try:
            pass
        except ValueError:
            pass

def gen():
    yield 1
    yield 2

def loop_gen_create():
    for _ in range(N):
        g = gen()
    return 0

def loop_gen_full():
    for _ in range(N):
        g = gen()
        next(g)
        next(g)

def loop_next_only():
    g = gen()
    try:
        for _ in range(N):
            next(g)
    except StopIteration:
        pass

def loop_range_iter():
    for _ in range(N):
        it = iter(range(2))

CASES = [
    ("loop_catch_only", loop_catch_only),
    ("loop_construct", loop_construct),
    ("loop_raise_prebuilt", loop_raise_prebuilt),
    ("loop_raise_new", loop_raise_new),
    ("loop_gen_create", loop_gen_create),
    ("loop_next_only", loop_next_only),
    ("loop_gen_full", loop_gen_full),
    ("loop_range_iter", loop_range_iter),
]
print("==", sys.version.split()[0], sys.implementation.name)
for label, fn in CASES:
    fn()
    best = None
    for _ in range(REPS):
        t0 = time.perf_counter()
        fn()
        dt = time.perf_counter() - t0
        ns = dt * 1e9 / N
        best = ns if best is None or ns < best else best
    print(f"{label:24s} {best:9.1f} ns/iter")
