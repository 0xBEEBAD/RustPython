"""Parity test for borrowed fast-local stack references.

LOAD_FAST_BORROW and LOAD_FAST_BORROW_LOAD_FAST_BORROW push non-owning stack
references. These checks pin the cases where the source fast-local slot can be
overwritten while a borrowed entry is still live: assignment, loops, exception
handlers, yields, f_locals proxies and traceback introspection.

  python test_borrow_fast.py
  rustpython test_borrow_fast.py
"""
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
        print(f"FAIL {name}: raised {type(e).__name__}: {e}, want {exc.__name__}")
    else:
        failures += 1
        print(f"FAIL {name}: no exception")


class Tagged:
    def __init__(self, name):
        self.name = name

    def __getitem__(self, key):
        return self.name


def label(value):
    return value.name if isinstance(value, Tagged) else value


# 1. Local borrowed in a loop, then reassigned on the next iteration.
def loop_reassign(n):
    a = 3
    total = 0
    for i in range(n):
        total += a
        a = i
    return total


check("loop local reassignment", loop_reassign(10), 39)


# 2. Save a local into a new name, then overwrite the original.
def use_after_reassign(a, b):
    x = a
    a = b
    return x


first, second = Tagged("first"), Tagged("second")
saved = use_after_reassign(first, second)
check("x = a; a = b value", label(saved), "first")
check("x = a; a = b identity", saved is first, True)


# 3. DELETE_FAST of an unbound local, and of a bound local.
def delete_unbound():
    del missing


check_raises(
    "DELETE_FAST unbound", delete_unbound, UnboundLocalError, "missing"
)


def delete_then_load():
    temp = Tagged("temp")
    del temp
    return temp


check_raises(
    "DELETE_FAST then LOAD_FAST", delete_then_load, UnboundLocalError, "temp"
)


# 4./5. f_locals writes while a borrowed local sits on the eval stack.
# Keep the replaced object alive so this test also passes on CPython builds
# whose f_locals write does not promote the borrowed stack entry.
_keep_alive = []


def write_local(frame, name, value):
    _keep_alive.append(frame.f_locals.get(name))
    frame.f_locals[name] = value
    return 0


def index_after_current_write(a):
    return a[write_local(sys._getframe(), "a", "replaced")]


check(
    "f_locals write to current frame between load and use",
    label(index_after_current_write(Tagged("orig"))),
    "orig",
)


def write_caller_local(name, value):
    write_local(sys._getframe(1), name, value)
    return 0


def index_after_caller_write(a):
    return a[write_caller_local("a", "caller-replaced")]


check(
    "callee writes caller f_locals during call",
    label(index_after_caller_write(Tagged("orig"))),
    "orig",
)


def caller_write_then_use(a):
    a[write_caller_local("a", "caller-replaced")]
    return a


check(
    "callee f_locals write visible after call",
    label(caller_write_then_use(Tagged("orig"))),
    "caller-replaced",
)


# 6. Generator suspended with a borrowed local below the yielded value; the
# resumed generator must observe f_locals writes made while suspended.
def gen_carrying_locals():
    a = "A"
    b = "B"
    got = (a, (yield b))
    yield (a, got)


g = gen_carrying_locals()
check("generator first yield", next(g), "B")
g.gi_frame.f_locals["a"] = "X"
g.gi_frame.f_locals["b"] = "Y"
check(
    "generator resume after f_locals write",
    next(g),
    ("X", ("A", None)),
)
check_raises("generator exhausted", lambda: next(g), StopIteration)


def gen_tagged_carry():
    a = Tagged("A")
    got = (a, (yield "pause"))
    yield (label(a), label(got[0]))


g = gen_tagged_carry()
check("tagged generator first yield", next(g), "pause")
_keep_alive.append(g.gi_frame.f_locals.get("a"))
g.gi_frame.f_locals["a"] = Tagged("X")
check(
    "tagged generator resume after f_locals write",
    next(g),
    ("X", "A"),
)


# 6b. The borrowed local below a yield must be promoted before the frame is
# suspended: a missing promotion shows up as a dead weakref after the
# f_locals write, without needing a use-after-free to crash.
_probe_ref = None


def gen_weak_probe():
    global _probe_ref
    a = Tagged("probe")
    _probe_ref = weakref.ref(a)
    a, (yield "pause")


g = gen_weak_probe()
check("weak-probe generator first yield", next(g), "pause")
g.gi_frame.f_locals["a"] = "replaced"
check("borrowed local promoted across yield", _probe_ref() is not None, True)
check_raises("weak-probe generator exhausted", lambda: next(g), StopIteration)
check("borrowed local released after resume", _probe_ref() is None, True)


# 7. Exception raised while a local is borrowed, caught by a handler that
# reassigns that local.
def raise_zero_division():
    return 1 // 0


def handler_reassigns_local(a):
    try:
        return a[raise_zero_division()]
    except ZeroDivisionError:
        a = Tagged("handler")
        return a


check(
    "except handler reassigns borrowed local",
    label(handler_reassigns_local(Tagged("orig"))),
    "handler",
)


def handler_then_loop(n):
    a = Tagged("start")
    out = []
    for i in range(n):
        try:
            if i % 2:
                out.append(label(a))
            else:
                raise ValueError(i)
        except ValueError:
            a = Tagged(f"caught{i}")
    return out


check("handler reassignment in loop", handler_then_loop(4), ["caught0", "caught2"])


# 8. Loop whose body fuses STORE_FAST + LOAD_FAST.
def loop_store_load(n):
    a = 0
    out = 0
    for i in range(n):
        # Same-line statements let the compiler fuse STORE_FAST + LOAD_FAST.
        b = a; out = b; a = i
    return out


check("loop with STORE_FAST_LOAD_FAST", loop_store_load(5), 3)


# 9. Inlined comprehension shadows and restores the outer local
# (LOAD_FAST_AND_CLEAR / STORE_FAST round-trip).
def comprehension_shadow(values):
    x = "outer"
    ys = [x for x in values]
    return x, ys


check(
    "inlined comprehension restores shadowed local",
    comprehension_shadow([1, 2, 3]),
    ("outer", [1, 2, 3]),
)


def comprehension_after_reassign(values):
    x = "outer"
    ys = [x * 2 for x in values]
    x = "changed"
    return x, ys


check(
    "inlined comprehension after reassignment",
    comprehension_after_reassign([1, 2]),
    ("changed", [2, 4]),
)


# 10. Traceback frame locals of a function that raised.
def raises_with_locals(a):
    b = a
    raise ValueError("boom")


try:
    raises_with_locals(Tagged("traceback"))
except ValueError as exc:
    tb = exc.__traceback__
    while tb is not None and tb.tb_frame.f_code.co_name != "raises_with_locals":
        tb = tb.tb_next
    check("traceback frame found", tb is not None, True)
    frame = tb.tb_frame
    check("traceback f_locals a", label(frame.f_locals["a"]), "traceback")
    check("traceback f_locals b", label(frame.f_locals["b"]), "traceback")
    frame.f_locals["a"] = "patched"
    check("traceback f_locals write", label(frame.f_locals["a"]), "patched")


# 10b. A borrowed local still on the eval stack when the function raises must
# stay alive through an f_locals write on the traceback frame.
_tb_probe_ref = None


def raises_with_borrowed_local(a):
    global _tb_probe_ref
    _tb_probe_ref = weakref.ref(a)
    return a[_undefined_borrow_probe]


try:
    raises_with_borrowed_local(Tagged("tb-borrow"))
except NameError as exc:
    tb = exc.__traceback__
    while (
        tb is not None
        and tb.tb_frame.f_code.co_name != "raises_with_borrowed_local"
    ):
        tb = tb.tb_next
    frame = tb.tb_frame
    check("raised frame keeps borrowed local", _tb_probe_ref() is not None, True)
    frame.f_locals["a"] = "patched"
    check(
        "traceback write keeps promoted local", _tb_probe_ref() is not None, True
    )
    frame.clear()
    check("traceback clear releases local", _tb_probe_ref() is None, True)


print("RESULT", "FAIL" if failures else "OK")
sys.exit(1 if failures else 0)
