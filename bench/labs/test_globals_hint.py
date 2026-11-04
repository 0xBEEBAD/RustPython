"""Parity test for cached global lookup invalidation.

LOAD_GLOBAL installs a version+index cache on first execution. These checks
pin that any globals mutation (rebind, delete, builtin shadowing) is observed
afterwards, including inside long-running loops and after the cache has been
reused many times.

  python test_globals_hint.py
  rustpython test_globals_hint.py
"""
import sys

failures = 0


def check(name, got, want):
    global failures
    if got == want:
        print(f"PASS {name}")
    else:
        failures += 1
        print(f"FAIL {name}: got {got!r}, want {want!r}")


def check_raises(name, fn, exc):
    global failures
    try:
        fn()
    except exc:
        print(f"PASS {name}")
    except BaseException as e:
        failures += 1
        print(f"FAIL {name}: raised {type(e).__name__}: {e}, want {exc.__name__}")
    else:
        failures += 1
        print(f"FAIL {name}: no exception")


# 1. A global rebound while a function's LOAD_GLOBAL site is hot.
G = 1


def read_loop(n):
    total = 0
    for _ in range(n):
        total += G
    return total


check("initial global", read_loop(5000), 5000)
G = 5
check("rebound global", read_loop(10), 50)
G = -3
check("negative global", read_loop(4), -12)

# 2. Deleting and re-creating the name.
D = 7


def read_d():
    return D


check("global before delete", read_d(), 7)
del D
check_raises("global after delete", read_d, NameError)
D = 9
check("global recreated", read_d(), 9)

# 3. Builtin shadowing after the builtin path specialized.
def call_len(x):
    return len(x)


check("builtin len", call_len([1, 2]), 2)
_len = len


def fake_len(_x):
    return 42


len = fake_len
check("shadowed builtin", call_len([1, 2]), 42)
del len
len = _len
check("restored builtin", call_len([1, 2]), 2)
del _len

# 4. Name missing at specialization time, defined later.
def read_late():
    return LATE


check_raises("late global missing", read_late, NameError)
LATE = "now"
check("late global defined", read_late(), "now")

# 5. Mutation inside the loop body itself must be observed on the next read.
M = 0


def mutate_and_read(n):
    global M
    seen = []
    for i in range(n):
        M = i
        seen.append(M)
    return seen


check("mutate inside loop", mutate_and_read(5), [0, 1, 2, 3, 4])

# 6. globals() writes are visible to the cached site.
V = 1


def read_v():
    return V


check("before globals write", read_v(), 1)
globals()["V"] = 11
check("after globals write", read_v(), 11)

# 7. Module dict via __dict__ item assignment.
W = 2


def read_w():
    return W


check("before dict item", read_w(), 2)
sys.modules[__name__].__dict__["W"] = 22
check("after dict item", read_w(), 22)

print("RESULT", "FAIL" if failures else "OK")
sys.exit(1 if failures else 0)
