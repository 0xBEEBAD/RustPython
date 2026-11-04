"""Parity checks for the slim (prefix-free) int allocation path."""

import gc
import sys
import weakref

failures = []


def check(name, cond, detail=""):
    if not cond:
        failures.append(f"{name}: {detail}")


# --- base ints are not GC-tracked, like CPython ---
check("is_tracked_small", gc.is_tracked(1) is False, gc.is_tracked(1))
check("is_tracked_big", gc.is_tracked(10**30) is False, gc.is_tracked(10**30))

# --- ints survive heavy allocation churn (freelist reuse of slim husks) ---
acc = 0
for i in range(200000):
    acc += i * 3
check("churn", acc == sum(i * 3 for i in range(200000)), acc)

# --- big int arithmetic after churn ---
big = 1
for _ in range(64):
    big *= 0x123456789ABCDEF
check("big_mul", (big // 0x123456789ABCDEF**63) == 0x123456789ABCDEF, hex(big % 97))

# --- ints as dict keys / set members ---
d = {i: i * i for i in range(4096)}
check("dict", d[1234] == 1234 * 1234 and len(d) == 4096, len(d))
s = set(range(4096))
check("set", len(s) == 4096 and 4095 in s, len(s))

# --- non-int payloads still work (full-prefix path) ---
check("str_prefix", "abc" * 3 == "abcabcabc", "")
check("float", 0.5 + 0.25 == 0.75, "")
check("tuple_prefix", (1, "a", 2.5)[1] == "a", "")

# --- weakrefs to plain ints are rejected ---
try:
    weakref.ref(5)
except TypeError:
    pass
else:
    failures.append("weakref: int unexpectedly weakrefable")


# --- int subclasses get a dict and stay GC-tracked ---
class MyInt(int):
    pass


m = MyInt(7)
m.tag = "hello"
check("subclass_value", m + 1 == 8, m + 1)
check("subclass_attr", m.tag == "hello", getattr(m, "tag", None))
check("subclass_isinstance", isinstance(m, int), type(m))
check("subclass_tracked", gc.is_tracked(m) is True, gc.is_tracked(m))
check("subclass_dict", set(m.__dict__) == {"tag"}, m.__dict__)
del m
gc.collect()

# --- int subclasses cannot add slots (matches CPython) ---
try:
    class SlotInt(int):
        __slots__ = ("x",)
except TypeError:
    pass
else:
    failures.append("slots: nonempty __slots__ unexpectedly allowed on int subclass")


class EmptySlotsInt(int):
    __slots__ = ()


es = EmptySlotsInt(11)
check("emptyslots_value", es + 1 == 12, es + 1)
check("emptyslots_tracked", gc.is_tracked(es) is True, gc.is_tracked(es))
try:
    es.x = 1
except AttributeError:
    pass
else:
    failures.append("emptyslots: attribute assignment unexpectedly allowed")

# --- subclass instances survive collection cycles ---
class Node(int):
    pass


n = Node(3)
n.self_ref = n
del n
gc.collect()

# --- bool is an int payload: still correct after slim allocation changes ---
check("bool", (True + True) == 2 and isinstance(True, int), True)

# --- exceptions/copies still fine ---
check("copy", int("123") + 0 == 123, int("123"))
check("hex", hex(255) == "0xff", hex(255))
check("sys_getsizeof", isinstance(sys.getsizeof(1), int), sys.getsizeof(1))

if failures:
    print("FAIL")
    for f in failures:
        print(" -", f)
    sys.exit(1)
print("PASS: slim header parity")
