"""Parity test for the no-__init__ class-call fast path.

The fast path allocates a heap-type instance directly when the call site sees
zero args, the default tp_new/tp_alloc, and object.__init__. These cases pin
the semantics that must survive: __init__/__new__ overrides, defaults,
abstract classes, __slots__, metaclass __call__, inheritance, and deopt after
the class is mutated following specialization.

  python test_classcall_fast.py
  rustpython test_classcall_fast.py
"""
import abc
import sys

failures = 0


def check(name, got, want):
    global failures
    if got == want:
        print(f"PASS {name}")
    else:
        failures += 1
        print(f"FAIL {name}: got {got!r}, want {want!r}")


def check_raises(name, fn, exc, message=None):
    global failures
    try:
        fn()
    except exc as e:
        if message is not None and message not in str(e):
            failures += 1
            print(f"FAIL {name}: {str(e)!r} missing {message!r}")
            return
        print(f"PASS {name}")
    except BaseException as e:
        failures += 1
        print(f"FAIL {name}: raised {type(e).__name__}, want {exc.__name__}")
    else:
        failures += 1
        print(f"FAIL {name}: no exception")


# 1. Plain class: distinct instances, correct type.
class Plain:
    pass


a = Plain()
b = Plain()
check("plain type", type(a).__name__, "Plain")
check("plain distinct", a is not b, True)
check("plain isinstance", isinstance(a, Plain), True)
check("plain no dict shadowing", hasattr(a, "__dict__"), True)
a.x = 5
check("plain attrs", a.x, 5)

# 2. Class with __init__ (defaults, args, extra attributes).
class WithInit:
    def __init__(self, x, y=2):
        self.x = x
        self.y = y


w = WithInit(1)
check("init default", (w.x, w.y), (1, 2))
w = WithInit(1, 3)
check("init args", (w.x, w.y), (1, 3))
check_raises("init missing arg", lambda: WithInit(), TypeError)

# 3. __new__ override still runs.
class CustomNew:
    def __new__(cls):
        obj = super().__new__(cls)
        obj.via_new = True
        return obj


check("custom __new__", CustomNew().via_new, True)

# 4. Abstract classes cannot be instantiated.
class Abstract(abc.ABC):
    @abc.abstractmethod
    def work(self):
        ...


class Concrete(Abstract):
    def work(self):
        return 1


# RustPython's wording omits CPython's "Can't instantiate abstract class"
# prefix; both must mention the unimplemented abstract method.
check_raises("abstract rejected", lambda: Abstract(), TypeError,
             "abstract method 'work'")
check("concrete abc ok", Concrete().work(), 1)

# 5. __slots__ classes.
class Slotted:
    __slots__ = ("v",)


s = Slotted()
s.v = 9
check("slots", s.v, 9)
check_raises("slots no dict", lambda: setattr(s, "other", 1), AttributeError)

# 6. Metaclass __call__ override is honored.
class Meta(type):
    def __call__(cls, *args, **kwargs):
        obj = super().__call__(*args, **kwargs)
        obj.from_meta = True
        return obj


class WithMeta(metaclass=Meta):
    pass


check("metaclass call", WithMeta().from_meta, True)

# 7. Inheritance: subclass of a plain class, and of a class with __init__.
class Child(Plain):
    pass


check("child type", type(Child()).__name__, "Child")


class Child2(WithInit):
    pass


check("child init inherited", Child2(7).x, 7)

# 8. object.__new__ returning a foreign instance is not bypassed.
class WeirdNew:
    def __new__(cls):
        return 42


check("weird __new__", WeirdNew(), 42)

# 9. Deopt after mutating the class following specialization: run the call
#    site many times first so it specializes, then install __init__.
class Late:
    pass


for _ in range(2000):
    Late()

probe = Late()
check("late no init attr", hasattr(probe, "late_init"), False)
Late.__init__ = lambda self: setattr(self, "late_init", True)
probe = Late()
check("late installed init runs", getattr(probe, "late_init", None), True)
for _ in range(2000):
    Late()
check("late init still runs", Late().late_init, True)

# 10. Revealing that zero-arg calls still raise the CPython message.
class NoInit:
    pass


check_raises("no-arg class with arg", lambda: NoInit(1), TypeError,
             "takes no arguments")

print("RESULT", "FAIL" if failures else "OK")
sys.exit(1 if failures else 0)
