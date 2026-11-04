"""Parity test for exact-container subscript fast paths (list/tuple/dict).

Exact types with exact index operands take a direct lookup; everything else
(subclasses, slices, missing keys, out-of-range indices, odd index types) must
keep the generic protocol and its exact error behaviour.

  python test_subscr_fast.py
  rustpython test_subscr_fast.py
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


lst = [10, 20, 30]
tup = (10, 20, 30)
dct = {"k": 1, 2: "two"}

# 1. Basics.
check("list index", lst[1], 20)
check("list negative", lst[-1], 30)
check("tuple index", tup[0], 10)
check("tuple negative", tup[-2], 20)
check("dict str key", dct["k"], 1)
check("dict int key", dct[2], "two")
check("dict missing type", type(dct.get("missing")), type(None))

# 2. Errors fall back to the generic protocol.
check_raises("list oob", lambda: lst[10], IndexError)
check_raises("list negative oob", lambda: lst[-10], IndexError)
check_raises("tuple oob", lambda: tup[10], IndexError)
check_raises("dict missing key", lambda: dct["missing"], KeyError)
check_raises("list str index", lambda: lst["a"], TypeError)

# 3. Slices still work (str fast path and generic containers).
check("list slice", lst[0:2], [10, 20])
check("tuple slice", tup[::-1], (30, 20, 10))
check("list slice assign", (lambda l: (l.__setitem__(slice(0, 1), [9]), l)[1])([1, 2]), [9, 2])

# 4. Subclasses deopt to their own __getitem__.
class WeirdList(list):
    def __getitem__(self, item):
        return "WL"


class WeirdTuple(tuple):
    def __getitem__(self, item):
        return "WT"


class WeirdDict(dict):
    def __getitem__(self, item):
        return "WD"


check("list subclass", WeirdList([1, 2])[0], "WL")
check("tuple subclass", WeirdTuple((1, 2))[0], "WT")
check("dict subclass", WeirdDict({"a": 1})["a"], "WD")

# 5. Mutation visible through the fast path.
m = [1]
m.append(2)
check("after append", m[1], 2)
m[0] = 5
check("after setitem", m[0], 5)

# 6. Index objects with __index__ still work (generic path).
class Idx:
    def __index__(self):
        return 1


check("index object list", lst[Idx()], 20)
check("index object tuple", tup[Idx()], 20)
check("bool index", lst[True], 20)

# 7. Nested subscripts.
nested = [[1, 2], [3, 4]]
check("nested", nested[1][0], 3)
check("dict of list", {"a": [7]}["a"][0], 7)

print("RESULT", "FAIL" if failures else "OK")
sys.exit(1 if failures else 0)
