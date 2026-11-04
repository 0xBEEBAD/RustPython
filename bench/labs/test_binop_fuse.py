"""Parity checks for the LOAD_SMALL_INT+BINARY_OP fused instruction."""

import sys
import traceback

failures = []


def check(name, cond, detail=""):
    if not cond:
        failures.append(f"{name}: {detail}")


# --- plain int fast path ---
def add_one(x):
    return x + 1


def sub_one(x):
    return x - 1


def mul_two(x):
    return x * 2


def store_add(x):
    x += 7
    return x


def store_inplace(x):
    x = x + 3
    return x


check("add", add_one(41) == 42, add_one(41))
check("sub", sub_one(41) == 40, sub_one(41))
check("mul", mul_two(21) == 42, mul_two(21))
check("store_add", store_add(35) == 42, store_add(35))
check("store_inplace", store_inplace(39) == 42, store_inplace(39))
check("big", add_one(10**30) == 10**30 + 1, "big int")
check("neg_const", add_one(-5) == -4, add_one(-5))

# --- non-int left operand falls back to generic BINARY_OP ---
check("float", add_one(0.5) == 1.5, add_one(0.5))
check("str_mul", mul_two("ab") == "abab", mul_two("ab"))
check("list_mul", mul_two([1]) == [1, 1], mul_two([1]))
check("bool", add_one(True) == 2, add_one(True))


class IntSub(int):
    def __add__(self, other):
        return "custom"


check("int_subclass", add_one(IntSub(1)) == "custom", add_one(IntSub(1)))


class RAdd:
    def __radd__(self, other):
        return ("radd", other)


def radd_case(x):
    return 1 + x


check("radd", radd_case(RAdd()) == ("radd", 1), radd_case(RAdd()))


class IAdd:
    def __iadd__(self, other):
        return "iadd"


check("iadd", store_add(IAdd()) == "iadd", store_add(IAdd()))

# --- exceptions from the operand still propagate with the right line ---
class Boom:
    def __add__(self, other):
        raise ValueError("boom")


try:
    add_one(Boom())
except ValueError as e:
    tb = e.__traceback__
    frames = []
    while tb is not None:
        frames.append(tb.tb_lineno)
        tb = tb.tb_next
    check("exc_raised", str(e) == "boom", str(e))
    check(
        "exc_lineno",
        len(frames) == 3 and frames[1] == add_one.__code__.co_firstlineno + 1,
        frames,
    )
else:
    failures.append("exc: no ValueError")


class BadAdd(int):
    def __add__(self, other):
        raise RuntimeError("bad")


try:
    add_one(BadAdd(1))
except RuntimeError as e:
    check("exc_subclass", str(e) == "bad", str(e))
else:
    failures.append("exc_subclass: no RuntimeError")

# --- loops keep their arithmetic exact ---
total = 0
for i in range(1000):
    total += i * 2
check("loop", total == sum(i * 2 for i in range(1000)), total)

# --- running under a tracer must not change results ---
events = []


def tracer(frame, event, arg):
    if event == "call":
        frame.f_trace_opcodes = True
    elif event == "opcode":
        events.append(frame.f_lasti)
    return tracer


def traced(x):
    y = x + 4
    x *= 3
    return x + y


sys.settrace(tracer)
try:
    traced_result = traced(10)
finally:
    sys.settrace(None)
check("traced_result", traced_result == 44, traced_result)

# --- generators and comprehensions ---
def gen(n):
    for i in range(n):
        yield i + 1


check("gen", list(gen(4)) == [1, 2, 3, 4], list(gen(4)))
check("comp", [i + 1 for i in range(4)] == [1, 2, 3, 4], [i + 1 for i in range(4)])


# --- local-pair fusion: `a OP b` with both operands in locals ---
def pair_add(a, b):
    return a + b


def pair_sub(a, b):
    return a - b


def pair_mul(a, b):
    return a * b


def pair_store(a, b):
    c = a + b
    return c


def pair_iadd(a, b):
    a += b
    return a


check("pair_add", pair_add(20, 22) == 42, pair_add(20, 22))
check("pair_sub", pair_sub(50, 8) == 42, pair_sub(50, 8))
check("pair_mul", pair_mul(6, 7) == 42, pair_mul(6, 7))
check("pair_store", pair_store(40, 2) == 42, pair_store(40, 2))
check("pair_iadd", pair_iadd(40, 2) == 42, pair_iadd(40, 2))
check("pair_big", pair_add(10**40, 10**40) == 2 * 10**40, "big pair")
check("pair_float", pair_add(1.25, 2.25) == 3.5, pair_add(1.25, 2.25))
check("pair_str", pair_add("ab", "cd") == "abcd", pair_add("ab", "cd"))
check("pair_list", pair_add([1], [2]) == [1, 2], pair_add([1], [2]))
check("pair_bool", pair_add(True, True) == 2, pair_add(True, True))
check("pair_subclass", pair_add(IntSub(1), 2) == "custom", pair_add(IntSub(1), 2))
check("pair_mixed", pair_add(1, 2.5) == 3.5, pair_add(1, 2.5))
check("pair_unbound", pair_add(7, 8) == 15, pair_add(7, 8))


def pair_unbound_error():
    x = 1
    try:
        return x + y
    except NameError:
        return "unbound"


check("pair_unbound_local", pair_unbound_error() == "unbound", pair_unbound_error())


class PairBoom:
    def __add__(self, other):
        raise ValueError("pair boom")


try:
    pair_add(PairBoom(), PairBoom())
except ValueError as e:
    check("pair_exc", str(e) == "pair boom", str(e))
else:
    failures.append("pair_exc: no ValueError")

# loop over local pairs
def pair_loop(n):
    total = 0
    i = 0
    while i < n:
        total = pair_add(total, i)
        i = pair_add(i, 1)
    return total


check("pair_loop", pair_loop(100) == sum(range(100)), pair_loop(100))

# --- float and str pairs ride the same fused dispatch ---
def pair_fadd(a, b):
    return a + b


def pair_fsub(a, b):
    return a - b


def pair_fmul(a, b):
    return a * b


check("pair_fadd", pair_fadd(1.5, 2.25) == 3.75, pair_fadd(1.5, 2.25))
check("pair_fsub", pair_fsub(2.5, 0.125) == 2.375, pair_fsub(2.5, 0.125))
check("pair_fmul", pair_fmul(2.5, 4.0) == 10.0, pair_fmul(2.5, 4.0))
check("pair_fmixed", pair_fadd(1.5, 2) == 3.5, pair_fadd(1.5, 2))
check("pair_fstr", pair_fadd("a", "b") == "ab", pair_fadd("a", "b"))
check("pair_fstr_empty", pair_fadd("", "") == "", pair_fadd("", ""))


class FloatSub(float):
    def __add__(self, other):
        return "fsub"


check("pair_float_subclass", pair_fadd(FloatSub(1.0), 2.0) == "fsub", pair_fadd(FloatSub(1.0), 2.0))


def float_loop(n):
    total = 0.0
    i = 0.0
    while i < n:
        total += i * 0.5
        i += 1.0
    return total


check("float_loop", abs(float_loop(50) - sum(j * 0.5 for j in range(50))) < 1e-9, float_loop(50))


def build(n):
    s = ""
    for i in range(n):
        s = pair_fadd(s, "x")
    return s


check("str_loop", len(build(200)) == 200, len(build(200)))

# --- dis still decodes every instruction (no unknown/garbage args) ---
import dis

for instr in dis.get_instructions(traced):
    check("dis_argtype", instr.arg is None or isinstance(instr.arg, (int, str)), instr)

if failures:
    print("FAIL")
    for f in failures:
        print(" -", f)
    sys.exit(1)
print("PASS: binop fusion parity")
