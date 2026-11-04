"""Parity checks for the LOAD_FAST_BORROW pair + COMPARE_OP fused instruction."""

import sys

failures = []


def check(name, cond, detail=""):
    if not cond:
        failures.append(f"{name}: {detail}")


def lt(a, b):
    return a < b


def le(a, b):
    return a <= b


def eq(a, b):
    return a == b


def ne(a, b):
    return a != b


def gt(a, b):
    return a > b


def ge(a, b):
    return a >= b


OPS = [("<", lt), ("<=", le), ("==", eq), ("!=", ne), (">", gt), (">=", ge)]

VALUES = [
    0, 1, -1, 2**70, -(2**70), 1.5, -0.0, 0.0, True, False, None,
    "a", "b", "", (1, 2), [1, 2], [1, 3], (1,), 3, 3.0, "3",
]

for name, fn in OPS:
    for a in VALUES:
        for b in VALUES:
            try:
                expected = eval(f"a {name} b", {"a": a, "b": b})
            except Exception as exc:  # noqa: BLE001 - record the error type instead
                expected = ("error", type(exc).__name__)
            try:
                got = fn(a, b)
            except Exception as exc:  # noqa: BLE001
                got = ("error", type(exc).__name__)
            if got != expected:
                failures.append(f"{name} {a!r} {b!r}: got {got!r} want {expected!r}")

# operator overloads that return non-bools must be honored unchanged
class Weird:
    def __lt__(self, other):
        return "not-a-bool"

    def __eq__(self, other):
        return 42


check("weird_lt", lt(Weird(), Weird()) == "not-a-bool", lt(Weird(), Weird()))
check("weird_eq", eq(Weird(), Weird()) == 42, eq(Weird(), Weird()))
# reflected __lt__ answers , exactly like CPython
check("weird_gt", gt(Weird(), Weird()) == "not-a-bool", gt(Weird(), Weird()))


class IntLike(int):
    def __lt__(self, other):
        return "subclass"


check("int_subclass_lt", lt(IntLike(1), 2) == "subclass", lt(IntLike(1), 2))
check("int_subclass_gt", gt(2, IntLike(1)) == "subclass", gt(2, IntLike(1)))


class Boom:
    def __eq__(self, other):
        raise RuntimeError("boom")

    def __lt__(self, other):
        raise RuntimeError("boom")


try:
    eq(Boom(), Boom())
except RuntimeError as e:
    check("eq_raises", str(e) == "boom", str(e))
else:
    failures.append("eq_raises: no RuntimeError")

# NaN must keep IEEE semantics through the generic path
nan = float("nan")
check("nan_lt", lt(nan, 1.0) is False, lt(nan, 1.0))
check("nan_ne", ne(nan, 1.0) is True, ne(nan, 1.0))
check("nan_eq_self", eq(nan, nan) is False, eq(nan, nan))

# comparison chains
def chain(a, b, c):
    return a < b < c


check("chain_true", chain(1, 2, 3) is True, chain(1, 2, 3))
check("chain_false", chain(1, 3, 2) is False, chain(1, 3, 2))
check("chain_float", chain(1.0, 2.5, 3.0) is True, chain(1.0, 2.5, 3.0))


def chain_mixed(a, b, c):
    return a == b == c == a


check("chain_mixed", chain_mixed(1, 1, 1) is True, chain_mixed(1, 1, 1))
check("chain_mixed2", chain_mixed(1, 1, 2) is False, chain_mixed(1, 1, 2))


def chain_raises(a, b, c):
    return a < b < c


try:
    chain_raises(Boom(), 1, 2)
except RuntimeError as e:
    check("chain_raises", str(e) == "boom", str(e))
else:
    failures.append("chain_raises: expected RuntimeError")

# while loops and sorting conditions
def count_up(limit):
    i = 0
    total = 0
    while i < limit:
        total += i
        i += 1
    return total


check("while_loop", count_up(1000) == sum(range(1000)), count_up(1000))


def clamp(value, low, high):
    if value < low:
        return low
    if value > high:
        return high
    return value


check("clamp_low", clamp(-5, 0, 10) == 0, clamp(-5, 0, 10))
check("clamp_high", clamp(50, 0, 10) == 10, clamp(50, 0, 10))
check("clamp_mid", clamp(5.0, 0, 10) == 5.0, clamp(5.0, 0, 10))


def bubble(data):
    items = list(data)
    n = len(items)
    swapped = True
    while swapped:
        swapped = False
        for i in range(n - 1):
            if items[i] > items[i + 1]:
                items[i], items[i + 1] = items[i + 1], items[i]
                swapped = True
    return items


check("bubble", bubble([5, 3, 8, 1, 9, 2]) == [1, 2, 3, 5, 8, 9], bubble([5, 3, 8, 1, 9, 2]))
check("bubble_f", bubble([2.5, 1.5, 3.0]) == [1.5, 2.5, 3.0], bubble([2.5, 1.5, 3.0]))

# unbound local in the second slot must still report the right variable
def unbound_second(a):
    return a < missing_local


try:
    unbound_second(1)
except NameError as e:
    check("unbound_global", "missing_local" in str(e), str(e))
else:
    failures.append("unbound_global: expected NameError")


def unbound_slot(a, b):
    if a > 1000:
        return b
    del b
    return a < b


try:
    unbound_slot(1, 2)
except UnboundLocalError as e:
    check("unbound_del_local", "b" in str(e), str(e))
else:
    failures.append("unbound_del_local: expected UnboundLocalError")

# tracing must not change any outcome
events = []


def tracer(frame, event, arg):
    if event == "call":
        frame.f_trace_opcodes = True
    return tracer


sys.settrace(tracer)
try:
    traced_ok = [lt(1, 2), eq(1.0, 1), chain(1, 2, 3), count_up(20) == sum(range(20))]
finally:
    sys.settrace(None)
check("traced", traced_ok == [True, True, True, True], traced_ok)

# --- small-int constant comparisons: LOAD_SMALL_INT + COMPARE_OP fusion ---
CONSTS = [0, 1, 5, 100, 255, 256, 1000, 2**40]


def const_cmp(a, k, which):
    if which == 0:
        return a < k
    if which == 1:
        return a <= k
    if which == 2:
        return a == k
    if which == 3:
        return a != k
    if which == 4:
        return a > k
    return a >= k


CONST_VALUES = [
    0, 1, 5, 255, 256, 1000, 2**40, -1, 1.5, 5.0, True, False, None, "5", (5,),
]
for k in CONSTS:
    for which in range(6):
        for a in CONST_VALUES:
            try:
                expected = eval("a %s k" % ["<", "<=", "==", "!=", ">", ">="][which], {"a": a, "k": k})
            except Exception as exc:  # noqa: BLE001
                expected = ("error", type(exc).__name__)
            try:
                got = const_cmp(a, k, which)
            except Exception as exc:  # noqa: BLE001
                got = ("error", type(exc).__name__)
            if got != expected:
                failures.append(
                    f"const {a!r} {['<','<=','==','!=','>','>='][which]} {k}: "
                    f"got {got!r} want {expected!r}"
                )

# constant-bounded loops
def count_const():
    i = 0
    total = 0
    while i < 50:
        total += i
        i += 1
    return total


check("const_loop", count_const() == sum(range(50)), count_const())


def down_const(n):
    hits = 0
    i = n
    while i >= 1:
        hits += 1
        i -= 1
    return hits


check("const_loop_down", down_const(30) == 30, down_const(30))


def eq_const(x):
    if x == 0:
        return "zero"
    if x == 1:
        return "one"
    if x == 255:
        return "max255"
    if x == 256:
        return "over255"
    return "other"


check(
    "const_eq",
    [eq_const(v) for v in (0, 1, 255, 256, 7)] == ["zero", "one", "max255", "over255", "other"],
    [eq_const(v) for v in (0, 1, 255, 256, 7)],
)

# unbound local in while-loop conditions
def unbound_const_loop():
    n = 0
    while n < target:  # noqa: F821 - target is a missing global on purpose
        n += 1
    return n


try:
    unbound_const_loop()
except NameError as e:
    check("const_loop_unbound", "target" in str(e), str(e))
else:
    failures.append("const_loop_unbound: expected NameError")

# tracing over the constant-compare path
def traced_const(n):
    total = 0
    for i in range(n):
        if i % 2 == 0:
            total += i
    return total


sys.settrace(tracer)
try:
    const_trace = traced_const(20)
finally:
    sys.settrace(None)
check("const_traced", const_trace == sum(i for i in range(20) if i % 2 == 0), const_trace)

if failures:
    print("FAIL")
    for f in failures[:25]:
        print(" -", f)
    print(f"({len(failures)} failures)")
    sys.exit(1)
print("PASS: compare fusion parity")
