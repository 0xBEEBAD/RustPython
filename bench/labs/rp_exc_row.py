"""bench.py's `raise/catch exc` row verbatim, with bench.py's own calibration and
time-boxed measurement, so the printed ops/s is directly comparable to the
recorded 955,894 (ours) and 4,504,017 (CPython).

    rp-lite-119.exe bench/labs/rp_exc_row.py
    cp314/python.exe bench/labs/rp_exc_row.py
"""
import sys
import time


def bench(name, fn, seconds=2.0):
    n = 1
    while True:
        t0 = time.perf_counter()
        fn(n)
        dt = time.perf_counter() - t0
        if dt > 0.05 or n >= 10_000_000:
            break
        n *= 10
    count = 0
    total = 0.0
    while total < seconds:
        t0 = time.perf_counter()
        fn(n)
        total += time.perf_counter() - t0
        count += n
    ops = count / total
    print(
        "%s %s: %-16s %14s ops/s  %8.1f ns/op  (n=%s)"
        % (
            sys.implementation.name,
            ".".join(map(str, sys.version_info[:3])),
            name,
            format(ops, ",.0f"),
            1e9 / ops,
            format(n, ","),
        )
    )
    return ops


def throw(i):
    raise ValueError(i)


def bench_exc(n):
    caught = 0
    for i in range(n):
        try:
            throw(i)
        except ValueError:
            caught += 1


bench("raise/catch exc", bench_exc, 2.0)
