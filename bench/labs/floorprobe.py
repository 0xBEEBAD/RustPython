"""Loop-floor probe: isolates iterator and per-iteration allocation costs."""
import itertools
import sys
import time

N = 300000
data = [None] * N


def t(label, work):
    work(5000)
    best = 1e9
    for _ in range(5):
        t0 = time.perf_counter()
        work(N)
        dt = time.perf_counter() - t0
        best = min(best, dt)
    print(f"{label:30s} {best / N * 1e9:8.1f} ns")


def range_loop(n):
    for _ in range(n):
        pass


def range_var(n):
    for i in range(n):
        x = i


def repeat_loop(n):
    for _ in itertools.repeat(None, n):
        pass


def biglist_loop(n):
    for _ in data:
        pass


def arith(n):
    s = 0
    for i in range(n):
        s += i * 2 - 1


t("for range(n)", range_loop)
t("for i in range(n): x=i", range_var)
t("for repeat(None, n)", repeat_loop)
t("for _ in big list", biglist_loop)
t("arith loop", arith)
