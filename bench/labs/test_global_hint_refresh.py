"""Regression test: specialized LOAD_GLOBAL sites must re-hint after the
module dict changes, and must never serve a stale value."""

import time

failures = []


def check(name, cond, detail=""):
    if not cond:
        failures.append(f"{name}: {detail}")


counter = 0


def read_global():
    return counter


def timed(iters=60000):
    for _ in range(2000):  # warm the specialization
        read_global()
    t0 = time.perf_counter()
    for _ in range(iters):
        read_global()
    return (time.perf_counter() - t0) / iters


before = timed()

# 1. the value must always be current, however often globals change
g = globals()
for i in range(40000):
    g[f"churn{i}"] = i
    counter = i
    if read_global() != i:
        failures.append(f"stale value at {i}: {read_global()}")
        break
for i in range(40000):
    del g[f"churn{i}"]

# 2. deleting and re-adding the loaded name itself
counter = 7
check("after-del", read_global() == 7, read_global())
del g["counter"]
try:
    read_global()
except NameError:
    pass
else:
    failures.append("missing global: expected NameError")
g["counter"] = 99
check("re-added", read_global() == 99, read_global())

# 3. rebinding through a different type and back
counter = "text"
check("rebound-str", read_global() == "text", read_global())
counter = None
check("rebound-none", read_global() is None, read_global())
counter = 0

# 4. add+del churn must not strand the site on the slow path
for _ in range(30000):
    g["tmp"] = 1
    del g["tmp"]
after = timed()
check("no-permanent-deopt", after < before * 1.35, f"before {before * 1e9:.0f} ns, after {after * 1e9:.0f} ns")

# 5. builtins-backed sites stay correct when a global shadows the builtin
def read_abs():
    return abs


check("builtin", read_abs()(-3) == 3, read_abs()(-3))
abs = lambda x: "shadowed"  # noqa: E731
check("shadowed", read_abs()(-3) == "shadowed", read_abs()(-3))
del g["abs"]
check("unshadowed", read_abs()(-3) == 3, read_abs()(-3))

if failures:
    print("FAIL")
    for f in failures[:10]:
        print(" -", f)
    raise SystemExit(1)
print(f"PASS: global hint refresh (before {before * 1e9:.0f} ns, after {after * 1e9:.0f} ns)")
