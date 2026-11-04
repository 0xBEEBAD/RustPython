"""Parity test for FOR_ITER + STORE_FAST fusion in the specialized iterators.

The interpreter stores the loop variable directly when the instruction after
FOR_ITER is a plain STORE_FAST. These checks pin loop semantics: loop variable
after the loop, break/else, continue, deletion, exceptions, unpacking, tracing
and monitoring.

  python test_for_iter_fuse.py
  rustpython test_for_iter_fuse.py
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


# 1. Plain accumulation over the three specialized iterators.
def sums():
    sr = 0
    for i in range(10):
        sr += i
    sl = 0
    for v in [1, 2, 3, 4]:
        sl += v
    st = 0
    for v in (5, 6, 7):
        st += v
    return sr, sl, st


check("range/list/tuple sums", sums(), (45, 10, 18))

# 2. Loop variable keeps its last value after the loop (range/list/tuple).
def last_value():
    for i in range(3):
        pass
    after_range = i
    for v in ["a", "b"]:
        pass
    after_list = v
    for w in (1, 2):
        pass
    after_tuple = w
    return after_range, after_list, after_tuple


check("loop variable after loop", last_value(), (2, "b", 2))

# 3. Empty iteration leaves the loop variable unbound.
def empty_loop():
    try:
        for x in []:
            pass
        return x
    except UnboundLocalError:
        return "unbound"


check("empty list loop leaves var unbound", empty_loop(), "unbound")

# 4. break stops before the next store; else only runs without break.
def break_else():
    out = []
    for i in range(10):
        if i == 3:
            break
        out.append(i)
    else:
        out.append("else")
    for i in range(0):
        pass
    else:
        out.append("empty-else")
    return out


check("break/else", break_else(), [0, 1, 2, "empty-else"])

# 5. continue runs the loop store each iteration.
def continue_sum():
    s = 0
    for i in range(10):
        if i % 2:
            continue
        s += i
    return s


check("continue", continue_sum(), 20)

# 6. Reassigning the loop variable inside the body is overwritten next round.
def reassign():
    seen = []
    for i in range(3):
        seen.append(i)
        i = 100
    return seen, i


check("reassign loop var", reassign(), ([0, 1, 2], 100))

# 7. Deleting the loop variable inside the body.
def delete_var():
    out = []
    for i in range(3):
        out.append(i)
        del i
    return out


check("delete loop var", delete_var(), [0, 1, 2])

# 8. Nested loops share the fusion path.
def nested():
    total = 0
    for i in range(3):
        for j in range(4):
            total += i * j
    return total


check("nested loops", nested(), 18)

# 9. Exception raised in the body unwinds from the fused store correctly.
def raise_in_body():
    for i in range(10):
        if i == 2:
            raise ValueError(i)
    return "never"


check_raises("exception in body", raise_in_body, ValueError)

# 10. Unpacking loops are not fused but must stay correct.
def unpacking():
    pairs = []
    for a, b in [(1, 2), (3, 4), (5, 6)]:
        pairs.append(a * 10 + b)
    return pairs


check("unpacking loop", unpacking(), [12, 34, 56])

# 11. Loop variable is visible through locals() after the store.
def locals_visible():
    for i in range(2):
        pass
    return locals()["i"]


check("locals() sees loop var", locals_visible(), 1)

# 12. Tracing still sees the loop body (fusion falls back under settrace).
events = []


def tracer(frame, event, arg):
    if event == "line" and frame.f_code.co_name == "traced_loop":
        events.append(frame.f_lineno)
    return tracer


def traced_loop(n):
    total = 0
    for i in range(n):
        total += i
    return total


sys.settrace(tracer)
try:
    traced = traced_loop(4)
finally:
    sys.settrace(None)
check("traced loop result", traced, 6)
check("tracing observed lines", len(events) > 0, True)

# 13. Monitoring instruction events still fire for the loop store.
mon = sys.monitoring
TOOL = 4
mon.use_tool_id(TOOL, "for-iter-test")
seen = []


def on_instruction(code, offset):
    if code.co_name == "monitored_loop":
        seen.append(offset)


mon.register_callback(TOOL, mon.events.INSTRUCTION, on_instruction)
mon.set_events(TOOL, mon.events.INSTRUCTION)


def monitored_loop():
    total = 0
    for i in range(3):
        total += i
    return total


try:
    total = monitored_loop()
finally:
    mon.set_events(TOOL, 0)
    mon.register_callback(TOOL, mon.events.INSTRUCTION, None)
    mon.free_tool_id(TOOL)
check("monitoring result", total, 3)
check("monitoring fired", len(seen) > 0, True)

# 14. Generator iteration goes through the same FOR_ITER + STORE_FAST shape.
def numbers(n):
    for i in range(n):
        yield i * 3


def gen_sum():
    total = 0
    for v in numbers(5):
        total += v
    return total


check("generator loop", gen_sum(), 30)

# 15. Breaking out of a generator loop leaves it closable.
def break_gen():
    g = numbers(100)
    out = []
    for v in g:
        out.append(v)
        if v >= 6:
            break
    g.close()
    return out


check("break out of generator loop", break_gen(), [0, 3, 6])

# 16. BINARY_OP followed by STORE_FAST (`x = a + b`) is fused the same way.
def binop_store(n):
    total = 0
    last = 0
    for i in range(n):
        last = i * 3 - 1
        total += last
    return total, last


check("binop store", binop_store(5), (25, 11))


def float_store(n):
    acc = 0.0
    last = 0.0
    for i in range(n):
        last = i * 0.5
        acc += last
    return acc, last


check("float binop store", float_store(4), (3.0, 1.5))


def binop_not_store(a, b):
    # Result returned directly: the next instruction is RETURN, not a store.
    return a + b


check("binop without store", binop_not_store(2, 3), 5)


class Adder:
    def __init__(self, v):
        self.v = v

    def __add__(self, other):
        if other.v == 99:
            raise RuntimeError("boom")
        return Adder(self.v + other.v)


def binop_store_user_obj(n):
    a = Adder(1)
    last = None
    for i in range(n):
        last = a + Adder(i)
    return last.v


check("user-object binop store", binop_store_user_obj(4), 4)
check_raises("raising binop does not store", lambda: binop_store_user_obj(200), RuntimeError)

print("RESULT", "FAIL" if failures else "OK")
sys.exit(1 if failures else 0)
