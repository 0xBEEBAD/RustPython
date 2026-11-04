"""Behavioral parity test for list.sort's exact float/int fast paths.

The fast paths must reproduce CPython's semantics exactly:
  - stable order for equal elements (observable through object identity),
  - NaN keeps CPython's timsort ordering (fast path must not change it),
  - subclasses with overridden comparisons deopt to the generic protocol,
  - key= and reverse= are unaffected.

  python test_sort_fast.py
  rustpython test_sort_fast.py
"""
import math
import random
import sys

failures = 0


def check(name, got, want):
    global failures
    if got == want:
        print(f"PASS {name}")
    else:
        failures += 1
        print(f"FAIL {name}: got {got!r}, want {want!r}")


def check_ok(name, cond, detail=""):
    global failures
    if cond:
        print(f"PASS {name}")
    else:
        failures += 1
        print(f"FAIL {name} {detail}")


def same_order(a, b):
    return len(a) == len(b) and all(x is y for x, y in zip(a, b))


# 1. Random floats: values match sorted(), and result is sorted.
rng = random.Random(1234)
for size in (0, 1, 2, 7, 500):
    data = [rng.uniform(-1000, 1000) for _ in range(size)]
    expect_vals = sorted(data)
    got = list(data)
    got.sort()
    check(f"floats values n={size}", got, expect_vals)

# 2. Stability for distinct-but-equal float objects (identity must be kept).
vals = [float("1.5") for _ in range(3)] + [float("0.5")] + [float("1.5") for _ in range(2)]
# interleave two groups with equal keys but distinct identities
a1, a2 = float("2.0"), float("2.0")
b1, b2 = float("1.0"), float("1.0")
data = [a1, b1, a2, b2]
data.sort()
check_ok("float stability identity", same_order(data, [b1, b2, a1, a2]), [id(x) for x in data])

# 3. Signed zero: -0.0 == 0.0, so stability keeps the original order.
negz, posz = -0.0, 0.0
data = [negz, posz]
data.sort()
check_ok("signed zero stable", same_order(data, [negz, posz]))
check_ok("signed zero values", data[0] == 0.0 and data[1] == 0.0)

# 4. NaN: result must match CPython's timsort behavior.
nan = float("nan")
data = [3.0, nan, 1.0, 2.0, nan, 0.5]
expect = sorted([3.0, nan, 1.0, 2.0, nan, 0.5])
got = [3.0, nan, 1.0, 2.0, nan, 0.5]
got.sort()
same = (len(got) == len(expect)) and all(
    (math.isnan(x) and math.isnan(y)) or (x == y) for x, y in zip(got, expect)
)
check_ok("nan ordering matches sorted()", same, f"{got} vs {expect}")

# 5. Float subclass overriding __lt__ must be used (deopt to protocol).
class WeirdFloat(float):
    def __lt__(self, other):
        return float(self) > float(other)


data = [WeirdFloat(1.0), WeirdFloat(3.0), WeirdFloat(2.0)]
data.sort()
check("float subclass deopt", [float(x) for x in data], [3.0, 2.0, 1.0])

# 6. Int subclass overriding __lt__ must be used.
class WeirdInt(int):
    def __lt__(self, other):
        return int(self) > int(other)


data = [WeirdInt(1), WeirdInt(3), WeirdInt(2)]
data.sort()
check("int subclass deopt", [int(x) for x in data], [3, 2, 1])

# 7. Mixed int/float uses the generic path and sorts numerically.
data = [2, 1.5, 3, 0.5, 2.5]
data.sort()
check("mixed numeric", data, [0.5, 1.5, 2, 2.5, 3])

# 8. key= and reverse= still work.
data = [3.0, 1.0, 2.0]
data.sort(reverse=True)
check("reverse floats", data, [3.0, 2.0, 1.0])
data = [-3.0, 1.0, -2.0]
data.sort(key=abs)
check("key floats", data, [1.0, -2.0, -3.0])

# 9. Int stability with distinct-but-equal objects.
j1, j2 = int("1000"), int("1000")
k1, k2 = int("50"), int("50")
data = [j1, k1, j2, k2]
data.sort()
check_ok("int stability identity", same_order(data, [k1, k2, j1, j2]), [id(x) for x in data])

# 10. Large ints (outside i64 in principle) still sort correctly.
big = [10**30, -(10**30), 5, -5, 0]
data = list(big)
data.sort()
check("big ints", data, sorted(big))

print("RESULT", "FAIL" if failures else "OK")
sys.exit(1 if failures else 0)
