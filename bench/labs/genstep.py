"""How much does one generator step cost, against CPython?

The bench case is 2.63x slower than the reference interpreter and it is a
single opcode (SEND), so this isolates the step itself: one generator that
yields a small int, driven for a fixed number of resumes, plus two controls -
the same loop without a generator (a plain function call) and a list iterator,
which is the cheapest iterator CPython has.
"""
import time


def gen(n):
    for i in range(n):
        yield i


def loop_only(n):
    total = 0
    for i in range(n):
        total += i
    return total


def call_each(n):
    def inner(i):
        return i
    total = 0
    for i in range(n):
        total += inner(i)
    return total


def timeit(fn, iters, runs=5):
    best = float("inf")
    for _ in range(runs):
        start = time.perf_counter()
        fn(iters)
        best = min(best, time.perf_counter() - start)
    return best


N = 1_000_000


def gen_steps(n):
    g = gen(n)
    total = 0
    for value in g:
        total += value
    return total


for label, fn in (("generator step", gen_steps), ("plain loop", loop_only),
                  ("call per item", call_each)):
    seconds = timeit(fn, N)
    print(f"{label:16s} {N / seconds / 1e6:8.3f} M ops/s   {seconds / N * 1e9:7.1f} ns/op")
