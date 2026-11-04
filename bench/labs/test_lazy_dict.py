"""Parity test for lazily created instance dictionaries.

Instances now start without a dict object; it is materialized on the first
attribute write or `__dict__` access. These checks pin the observable
semantics: dict identity, vars(), deletion, class-attribute lookup, slots
classes, pickling/copying, cycles and `__getattr__` fallback.

  python test_lazy_dict.py
  rustpython test_lazy_dict.py
"""
import copy
import gc
import pickle
import sys
import weakref

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


class Plain:
    attr = 7

    def m(self):
        return "m"


c = Plain()

# 1. Fresh instance: empty dict, class attributes still visible.
check("fresh dict", c.__dict__, {})
check("fresh vars", vars(c), {})
check("class attr", c.attr, 7)
check("method", c.m(), "m")
check("dict identity", c.__dict__ is c.__dict__, True)

# 2. First write creates the dict; identity stays stable afterwards.
c.x = 1
check("write value", c.x, 1)
check("write dict", c.__dict__, {"x": 1})
d = c.__dict__
c.y = 2
check("dict identity after writes", c.__dict__ is d, True)
check("write dict 2", c.__dict__, {"x": 1, "y": 2})

# 3. Mutating through the dict object is visible as an attribute.
c.__dict__["z"] = 3
check("dict mutation", c.z, 3)

# 4. Deletion.
del c.x
check("after del", c.__dict__, {"y": 2, "z": 3})
check_raises("del missing attr", lambda: delattr(c, "nope"), AttributeError)

# 5. Replacing __dict__.
c.__dict__ = {"q": 1}
check("replaced dict", (c.q, c.__dict__), (1, {"q": 1}))

# 6. dir() sees instance attributes and class attributes.
names = dir(c)
check("dir has q", "q" in names, True)
check("dir has attr", "attr" in names, True)
check("dir has method", "m" in names, True)

# 7. __slots__ classes have no instance dict at all.
class Slotted:
    __slots__ = ("s",)


s = Slotted()
check("slots no dict", hasattr(s, "__dict__"), False)
check_raises("slots vars", lambda: vars(s), TypeError)
s.s = 5
check("slots value", s.s, 5)


# 8. __getattr__ fallback on a lazily-dicted instance.
class WithGetattr:
    def __getattr__(self, name):
        return f"fallback:{name}"


check("getattr fallback", WithGetattr().missing, "fallback:missing")
w = WithGetattr()
w.real = 1
check("real attr wins", w.real, 1)
check("fallback still", w.other, "fallback:other")

# 9. Copy and pickle keep attributes.
p = Plain()
p.a = 1
p.b = [2, 3]
c2 = copy.copy(p)
c3 = copy.deepcopy(p)
check("copy dict", c2.__dict__, {"a": 1, "b": [2, 3]})
check("deepcopy dict", c3.__dict__, {"a": 1, "b": [2, 3]})
check("deepcopy independent", c3.b is p.b, False)
p4 = pickle.loads(pickle.dumps(p))
check("pickle dict", p4.__dict__, {"a": 1, "b": [2, 3]})

# 10. Cycles through instance dicts are collectable.
class Node:
    pass


n = Node()
n.self_ref = n
wr = weakref.ref(n)
del n
gc.collect()
check("cycle collected", wr(), None)

# 11. Inheritance: subclass instances also start lazy.
class Child(Plain):
    pass


ch = Child()
check("child fresh dict", ch.__dict__, {})
check("child class attr", ch.attr, 7)

# 12. An instance attribute added after the method-load site specialized must
#     still shadow the class attribute (the lock-free lazy-dict check feeds the
#     LOAD_ATTR method guard).
class Shadow:
    attr = 1

    def m(self):
        return "method"


ss = Shadow()
for _ in range(3000):
    check_last = ss.m()
check("specialized method call", check_last, "method")
check("lazy dict before shadow", ss.__dict__, {})
ss.m = "instance"
check("instance shadows method", ss.m, "instance")
check_raises("shadowed call raises", lambda: ss.m(), TypeError)
ss.attr = 2
check("instance shadows class attr", ss.attr, 2)
del ss.m
check("shadow removed", ss.m(), "method")
check("empty dict after delete", ss.__dict__, {"attr": 2})

print("RESULT", "FAIL" if failures else "OK")
sys.exit(1 if failures else 0)
