"""Per-operation price of the method *machinery* around a builtin string call.

The `string ops` case of bench/bench.py decomposes into two shapes - a method
fetch and a method call - so every row here is one such shape in an otherwise
identical loop, and the loop+store control is subtracted from all of them.

Rows separate the three paradoxes in the task:

* the same attribute fetched bare (`t = s.upper`) and fetched-and-called
  (`s.upper()`), on a str, a list and an instance attribute;
* the same callee reached inline, through a hoisted bound-method object, and
  through the unbound descriptor with an explicit self;
* the arity ladder 0/1/2 arguments, plus a drop-only row that prices
  `DELETE_FAST` and one reference decrement and nothing else.

    bench/labs/variants/rp-lite-113.exe bench/labs/mp_methodcall_price.py
    bench/labs/cp314/python.exe         bench/labs/mp_methodcall_price.py

The harness deliberately contains no `str.split` call of its own, so
`LUNA_STUB_MD=split` can price the descriptor call arm on `split` as well; an
earlier revision crashed the whole probe under that gate.

Ablation runs (RustPython only) need their scope variables set in the SAME
command as the control, or the gate does nothing silently:

    LUNA_ABLATE=mdstub LUNA_STUB_MD=split bash bench/labs/mp_gates.sh
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


s = "abcdefgh"
# Split rows the LUNA_STUB_STR-scoped gates may touch: the prefix is what keeps
# the interpreter's own strings out of the instrument.
sz = "ZZZabcdefgh"
lst = [1, 2, 3]
inst = Inst()
u = s.upper
up = str.upper
mth = inst.m0
mth1 = inst.m1

# (label, body lines)
CASES = [
    # control: iter(range) + LOAD_FAST + STORE_FAST, one reference swap
    ("ctl: t = s", ["t = s"]),
    ("drop only: t = u; del t", ["t = u", "del t"]),
    # --- fetches -------------------------------------------------------
    ("t = s.upper    (LOAD_ATTR, str)", ["t = s.upper"]),
    ("t = str.upper  (LOAD_ATTR on type)", ["t = str.upper"]),
    ("t = inst.m0    (LOAD_ATTR, py method)", ["t = inst.m0"]),
    ("t = lst.append (LOAD_ATTR, list)", ["t = lst.append"]),
    ("t = u          (LOAD_FAST, no work)", ["t = u"]),
    ("t = inst.x     (LOAD_ATTR, instance)", ["t = inst.x"]),
    # --- fused fetch+call ----------------------------------------------
    ("s.upper()      (0 arg, exact kernel)", ["s.upper()"]),
    ("t = s.upper()  (0 arg, stored)", ["t = s.upper()"]),
    ("s.isascii()    (0 arg, no kernel)", ["s.isascii()"]),
    ("len(s)         (builtin fn, 1 arg)", ["t = len(s)"]),
    ("s.count('a')   (1 arg)", ["s.count('a')"]),
    ("s.split('x')   (1 arg, sep absent)", ["s.split('x')"]),
    ("sz.split('x')  (sep absent, scoped)", ["sz.split('x')"]),
    ("sz.split('d')  (1 arg, 2 pieces)", ["sz.split('d')"]),
    ("s.ljust(10, '-') (2 arg)", ["s.ljust(10, '-')"]),
    ("lst.count(1)   (1 arg, list)", ["lst.count(1)"]),
    ("inst.m0()      (0 arg, py method)", ["inst.m0()"]),
    ("inst.m1(1)     (1 arg, py method)", ["inst.m1(1)"]),
    # --- the same callee reached another way ---------------------------
    ("u()            (hoisted bound method)", ["u()"]),
    ("up(s)          (unbound descriptor)", ["up(s)"]),
    ("mth()          (hoisted py bound)", ["mth()"]),
    ("mth1(1)        (hoisted py bound, 1a)", ["mth1(1)"]),
    ("str.upper(s)   (load + call)", ["str.upper(s)"]),
]

HEAD = [
    "def case(s, sz, lst, inst, u, up, mth, mth1):",
    "    t = s",
    "    for _ in range(%d):" % N,
]


def build(body_lines):
    src = "\n".join(HEAD + ["        " + line for line in body_lines]) + "\n"
    ns = {}
    exec(compile(src, "<probe>", "exec"), ns)
    return ns["case"]


def run(fn):
    args = (s, sz, lst, inst, u, up, mth, mth1)
    fn(*args)  # warm the specializers
    fn(*args)
    times = []
    for _ in range(REPEATS):
        t0 = time.perf_counter()
        fn(*args)
        times.append(time.perf_counter() - t0)
    return min(times) / N * 1e9


def main():
    print("version: %s" % sys.version.replace("\n", " ")[:60])
    print("interp: %s" % ("RustPython" if IS_RUSTPYTHON else "CPython"))
    print("LUNA_ABLATE=%r LUNA_STUB_MD=%r LUNA_STUB_STR=%r" % (
        os.environ.get("LUNA_ABLATE", ""),
        os.environ.get("LUNA_STUB_MD", ""),
        os.environ.get("LUNA_STUB_STR", ""),
    ))
    print("N=%d best-of-%d, ns/op; net = raw - control\n" % (N, REPEATS))
    results = []
    for name, body in CASES:
        results.append((name, run(build(body))))
    control = results[0][1]
    print("%-38s %8s %8s" % ("case", "raw", "net"))
    for name, raw in results:
        print("%-38s %8.1f %8.1f" % (name, raw, raw - control))


if __name__ == "__main__":
    main()
