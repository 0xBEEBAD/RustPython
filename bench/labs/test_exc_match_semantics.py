"""Except-clause matching semantics pinned against CPython 3.14.7 behaviour.

CPython matches with the real MRO subtype relation: neither
__instancecheck__ nor __subclasscheck__ can change the answer, and a
target that is not a BaseException *class* is rejected with one specific
message. Run on CPython and RustPython; both must print the same PASS.
"""
import sys

MSG = "catching classes that do not inherit from BaseException is not allowed"
failures = []


def check(name, fn, expected):
    try:
        got = fn()
    except BaseException as e:
        got = "%s: %s" % (type(e).__name__, e)
    if got != expected:
        failures.append("%-28s got %r expected %r" % (name, got, expected))
    else:
        print("ok %-28s %s" % (name, got))


def hook(value_sub, value_inst):
    ns = {"calls": 0}

    class Meta(type):
        def __subclasscheck__(cls, sub):
            ns["calls"] += 1
            return value_sub

        def __instancecheck__(cls, obj):
            ns["calls"] += 1
            return value_inst

    class Exc(Exception, metaclass=Meta):
        pass

    class Real(Exc):
        pass

    class Unrelated(Exception):
        pass

    ns["types"] = (Exc, Real, Unrelated)
    return ns


def match_of(cls, given):
    def run():
        try:
            try:
                raise cls("v")
            except given:
                return "MATCH"
            except cls:
                return "no"
        except BaseException as e:
            return "err:%s" % type(e).__name__

    return run


# 1. the answer is always the real MRO relation, whatever the hooks say
for sub, inst in ((True, True), (False, False), (False, True), (True, False)):
    ns = hook(sub, inst)
    Exc, Real, Unrelated = ns["types"]
    label = "hooks sub=%s inst=%s" % (sub, inst)
    check(label + " exact", match_of(Exc, Exc), "MATCH")
    check(label + " subclass", match_of(Real, Exc), "MATCH")
    check(label + " unrelated", match_of(Unrelated, Exc), "no")

# 2. a raising hook does not break matching
def raising_hook():
    class Meta(type):
        def __subclasscheck__(cls, sub):
            raise ValueError("hook")

    class Exc(Exception, metaclass=Meta):
        pass

    try:
        raise KeyError("k")
    except Exc:
        return "matched wrongly"
    except KeyError:
        return "matched KeyError"


check("raising subclasscheck", raising_hook, "matched KeyError")

# 3. targets that are not BaseException classes are rejected with one message
class Plain:
    pass


def _raises(fn):
    try:
        return fn()
    except BaseException as e:
        return "%s: %s" % (type(e).__name__, e)


def instance_target():
    class F(Exception):
        pass

    def go():
        try:
            raise F("i")
        except F():
            pass

    return _raises(go)


def union_target():
    def go():
        try:
            raise ValueError("u")
        except (ValueError | TypeError):
            pass

    return _raises(go)


def plain_class_target():
    def go():
        try:
            raise ValueError("p")
        except Plain:
            pass

    return _raises(go)


def tuple_bad_element():
    def go():
        try:
            raise ValueError("t")
        except (Plain, ValueError):
            pass

    return _raises(go)


def tuple_of_exception():
    def go():
        try:
            raise ValueError("ok")
        except (TypeError, ValueError):
            return "matched tuple"

    return _raises(go)


def abc_target():
    import collections.abc

    def go():
        try:
            raise ValueError("a")
        except collections.abc.Iterator:
            pass

    return _raises(go)


check("instance target", instance_target, "TypeError: " + MSG)
check("union target", union_target, "TypeError: " + MSG)
check("plain class target", plain_class_target, "TypeError: " + MSG)
check("tuple bad element", tuple_bad_element, "TypeError: " + MSG)
check("abc target", abc_target, "TypeError: " + MSG)
check("tuple of exceptions", tuple_of_exception, "matched tuple")

# 4. the handled exception is still the one raised, via the same relation
def base_class_catch():
    try:
        raise ZeroDivisionError("z")
    except Exception as e:
        return type(e).__name__


check("base class catch", base_class_catch, "ZeroDivisionError")

print("python", sys.version.split()[0], sys.implementation.name)
if failures:
    print("FAIL: %d case(s)" % len(failures))
    for f in failures:
        print("  " + f)
    sys.exit(1)
print("PASS: except-match semantics (%d cases)" % (0 if failures else 21))
