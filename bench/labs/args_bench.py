"""Wall-clock timing script for the exception args-plumbing A/B.

One line per case, `<case>  <ns> ns`, which is the format bench/labs/ab.ps1
parses. Cases are the bench/bench.py `bench_exc` shape plus the pieces that
build it, so a saving on the creation path shows up where it is claimed.

Run:
    powershell -File bench/labs/ab.ps1 -A <exeA> -B <exeB> -Script bench/labs/args_bench.py
"""

import sys
import time

REPS = 9
N = 200_000


def throw(i):
    raise ValueError(i)


def loop(n):
    for _ in range(n):
        pass


def bench_exc(n):
    caught = 0
    for i in range(n):
        try:
            throw(i)
        except ValueError:
            caught += 1


def raise_inline(n):
    for i in range(n):
        try:
            raise ValueError(i)
        except ValueError:
            pass


def create_only(n):
    for i in range(n):
        x = ValueError(i)


def create_noarg(n):
    for i in range(n):
        x = ValueError()


def raise_many_args(n):
    for i in range(n):
        try:
            raise ValueError(i, i, i)
        except ValueError:
            pass


def str_builtin(n):
    for i in range(n):
        x = str(i)


class NewOnly(ValueError):
    # A Python-level `__new__` keeps `type.__call__` from skipping the init
    # call, so this is the shape where BaseException.__init__ still runs.
    def __new__(cls, *a, **kw):
        return Exception.__new__(cls, *a)


def new_override(n):
    for i in range(n):
        NewOnly(i)


CASES = [
    ("loop floor", loop),
    ("bench_exc", bench_exc),
    ("raise inline", raise_inline),
    ("create only", create_only),
    ("create noarg", create_noarg),
    ("raise 3 args", raise_many_args),
    ("new override", new_override),
    ("str(i) control", str_builtin),
]


def main():
    for name, fn in CASES:
        best = float("inf")
        for _ in range(REPS):
            t0 = time.perf_counter()
            fn(N)
            dt = time.perf_counter() - t0
            if dt < best:
                best = dt
        print(f"{name}  {best / N * 1e9:.3f} ns")


if __name__ == "__main__":
    main()
