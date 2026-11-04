"""Dispatch floor: how much does one more instruction cost?

Each case runs a loop whose body is `k` copies of one primitive, so the slope
between k and k+1 is the marginal cost of that instruction - and comparing the
slope here with CPython's is the honest way to decide whether the next lever is
more superinstructions (dispatch-bound) or something inside the arms
(operation-bound). `per_instr` is printed for the shapes that matter.
"""
import sys
import time

N = 200_000
REPS = 5


def noop():
    pass


def make_case(body, k):
    """def f(n): for _ in range(n): <body> x k   (one indent level in)"""
    src = "def f(n):\n    for _ in range(n):\n"
    for i in range(k):
        src += f"        {body.format(i=i)}\n"
    ns = {"noop": noop, "G": 1}
    exec(src, ns)
    return ns["f"]


def time_case(fn, iters):
    fn(1000)
    best = None
    for _ in range(REPS):
        t0 = time.perf_counter()
        fn(iters)
        dt = time.perf_counter() - t0
        best = dt if best is None else min(best, dt)
    return best


# LOAD_CONST + STORE_FAST: the cheapest two-instruction pair, no caches, no
# specialization, no protocol.
STORES = "x{i} = 1"
# A specialized global load: LOAD_GLOBAL_MODULE carries 4 cache units.
GLOBALS = "y{i} = G"
# A zero-argument Python call: the whole frame machinery, per instruction.
CALLS = "z{i} = noop()"

SHAPES = [("store", STORES), ("global", GLOBALS), ("call", CALLS)]
KS = (1, 2, 4, 8)

results = {}
for name, body in SHAPES:
    for k in KS:
        fn = make_case(body, k)
        results[(name, k)] = time_case(fn, N) / N * 1e9

for name, _ in SHAPES:
    base = results[(name, 1)]
    print(f"{name}_1".ljust(12) + f"{base:8.1f} ns/iter")
    for k in KS[1:]:
        # marginal cost per *replication* of the shape, i.e. per instruction
        # group added
        per = (results[(name, k)] - results[(name, 1)]) / (k - 1)
        print(f"{name}_per{k}".ljust(12) + f"{per:8.1f} ns/group")

loop_floor = time_case(make_case("pass", 1), N) / N * 1e9
print("loop_floor".ljust(12) + f"{loop_floor:8.1f} ns/iter")
