"""Parity test for recursion-depth accounting and native stack headroom.

PyFunction calls may consume native stack per Python frame; the native stack
guard must not fire before sys.getrecursionlimit() does. This pins the depth
available to ordinary non-tail recursion, recursion through lru_cache (which
adds a wrapper frame and a kwargs-style call per level), and that the counter
is restored after calls return.

  python test_recursion_depth.py
  rustpython test_recursion_depth.py
"""
import functools
import sys

failures = 0


def check(name, got, want):
    global failures
    if got == want:
        print(f"PASS {name}")
    else:
        failures += 1
        print(f"FAIL {name}: got {got!r}, want {want!r}")


def check_true(name, cond):
    check(name, bool(cond), True)


BASE_LIMIT = sys.getrecursionlimit()


# 1. Ordinary non-tail recursion uses half of the limit and returns.
def countdown(n):
    if n == 0:
        return 0
    return countdown(n - 1) + 1


check("non-tail recursion 450", countdown(450), 450)

# 2. Each level of a memoized non-tail recursion is two Python frames
#    (wrapper + function); 200 levels must fit well inside the limit.
@functools.lru_cache(maxsize=None)
def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)


check("lru_cache fib(200)", fib(200), 280571172992510140037611932413038677189525)

# 3. *args/**kwargs forwarding recursion (a second frame per level).
def forward(fn):
    def inner(*args, **kw):
        return fn(*args, **kw)

    return inner


@functools.lru_cache(maxsize=None)
def fib_args(n):
    return fib_args(n - 1) + fib_args(n - 2) if n > 1 else n


check("kwargs-forwarded lru_cache fib(200)", forward(fib_args)(200), fib(200))

# 4. Calls do not leak recursion depth: after many calls the same headroom
#    remains.
for _ in range(3000):
    countdown(0)
check("depth after 3000 calls", countdown(450), 450)
check("limit unchanged", sys.getrecursionlimit(), BASE_LIMIT)

# 5. Exceeding the limit raises RecursionError, and the process recovers.
def unbounded(n):
    return unbounded(n + 1)


try:
    unbounded(0)
except RecursionError:
    print("PASS infinite recursion raises RecursionError")
except BaseException as e:
    failures += 1
    print(f"FAIL infinite recursion raised {type(e).__name__}: {e}")
else:
    failures += 1
    print("FAIL infinite recursion did not raise")

# 6. The depth counter unwound after the RecursionError.
check("depth recovered after RecursionError", countdown(450), 450)
check("lru_cache fib after RecursionError", fib(100), 354224848179261915075)

print("RESULT", "FAIL" if failures else "OK")
sys.exit(1 if failures else 0)
