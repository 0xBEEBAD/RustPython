"""Per-operation price of the method *machinery* around a builtin string call.

The `string ops` case of bench/bench.py decomposes into two shapes - a method
fetch and a method call - so every row here is one such shape in an otherwise
identical loop, and the loop+store control is subtracted from all of them.

Rows are chosen to separate the three paradoxes in the task:

* the same attribute fetched bare (`t = s.upper`) and fetched-and-called
  (`s.upper()`), on a str, a list and an instance attribute;
* the call reached inline, through a hoisted bound-method object, and through
  the unbound descriptor with an explicit self;
* the arity ladder 0/1/2 arguments, plus a pure drop row that prices
  `DELETE_FAST` and one reference decrement and nothing else.

Run it the same way on both interpreters:

    bench/labs/variants/rp-lite-113.exe bench/labs/mp_methodcall.py
    bench/labs/cp314/python.exe         bench/labs/mp_methodcall.py

Ablation runs (RustPython only) need their scope variables set or the gate does
nothing silently:

    LUNA_ABLATE=mdstub LUNA_STUB_MD=upper ...
    LUNA_STUB_STR=ZZZ  (for the rows whose receiver starts with ZZZ)
"""

import os
import sys
import time

N = 200_000
REPEATS = 5

IS_RUSTPYTHON = "RustPython" in sys.version


class Inst:
    def __init__(self):
        self.x = 1
    def m0(self):
        return 1
    def m1(self, a):
        return a
    def m2(self, a, b):
        return a


s = "abcdefgh"
# Split rows that the LUNA_STUB_STR-scoped gates may touch: the prefix is what
# keeps the interpreter's own strings out of the instrument.
sz = "ZZZabcdefgh"
lst = [1, 2, 3]
inst = Inst()
inst.x = 1
u = s.upper
up = str.upper
mth = inst.m0
mth1 = inst.m1
lu = lst.append
lc = lst.count
sentinel = 1

CASES = [
    # control: iter(range) + LOAD_FAST + STORE_FAST, one reference swap
    ("ctl: t = s", "t = s"),
    ("drop only: t = u; del t", "t = u\ndel t"),
    # --- fetches -------------------------------------------------------
    ("t = s.upper   (LOAD_ATTR, str)", "t = s.upper"),
    ("t = lst.append(LOAD_ATTR, list)", "t = lst.append"),
    ("t = u        (LOAD_FAST alias, no work)", "t = u"),
    ("t = inst.x    (LOAD_ATTR, instance)", "t = inst.x"),
    # --- fused fetch+call ----------------------------------------------
    ("s.upper()     (0 arg)", "s.upper()"),
    ("t = s.upper() (0 arg, stored)", "t = s.upper()"),
    ("s.count('a')  (1 arg)", "s.count('a')"),
    ("s.split('x')  (1 arg, sep absent)", "s.split('x')"),
    ("sz.split('d') (1 arg, 2 pieces)", "sz.split('d')"),
    ("sz.split('x') (sep absent, 1 piece)", "sz.split('x')"),
    ("s.ljust(10, '-') (2 arg)", "s.ljust(10, '-')"),
    ("lst.count(1)  (1 arg, list)", "lst.count(1)"),
    ("inst.m0()     (0 arg, py method)", "inst.m0()"),
    ("inst.m1(1)    (1 arg, py method)", "inst.m1(1)"),
    # --- the same callee reached another way ---------------------------
    ("u()           (hoisted bound method)", "u()"),
    ("up(s)         (unbound descriptor)", "up(s)"),
    ("mth()         (hoisted py bound method)", "mth()"),
    ("mth1(1)       (hoisted py bound, 1 arg)", "mth1(1)"),
    ("str.upper(s)  (attr load + call)", "str.upper(s)"),
]


def build(body):
    src = "def case(s, sz, lst, inst, u, up, lu, lc, mth, mth1, sentinel):\n    t = s\n    for _ in range(%d):\n        %s\n" % (
        N,
        "\n        ".join(body.split("\n")),
    )
    ns = {}
    exec(compile(src, "<probe>", "exec"), ns)
    return ns["case"], src


def run(fn):
    args = (s, sz, lst, inst, u, up, lu, lc, mth, mth1, sentinel)
    fn(*args)  # warm the specializers
    fn(*args)
    times = []
    for _ in range(REPEATS):
        t0 = time.perf_counter()
        fn(*args)
        times.append(time.perf_counter() - t0)
    return min(times) / N * 1e9


def main():
    print("python: %s" % sys.version.split()[0])
    print("interp: %s" % ("RustPython" if IS_RUSTPYTHON else "CPython"))
    print("LUNA_ABLATE=%r LUNA_STUB_MD=%r LUNA_STUB_STR=%r" % (
        os.environ.get("LUNA_ABLATE", ""),
        os.environ.get("LUNA_STUB_MD", ""),
        os.environ.get("LUNA_STUB_STR", ""),
    ))
    print("N=%d best-of-%d, ns/op; net = raw - control\n" % (N, REPEATS))
    results = []
    for name, body in CASES:
        fn, _ = build(body)
        results.append((name, run(fn)))
    control = results[0][1]
    print("%-38s %8s %8s" % ("case", "raw", "net"))
    print("%-38s %8.1f %8.1f" % (results[0][0], control, 0.0))
    for name, raw in results[1:]:
        print("%-38s %8.1f %8.1f" % (name, raw, raw - control))


if __name__ == "__main__":
    main()
