"""Which function in a script holds the heads of a fused opcode?

The census (paircensus.py) says how many heads a fusion emits; a small count only
matters if those heads sit in a hot loop, so this prints the enclosing function
and its first line for every code object that contains the opcode.

    target/release/rustpython.exe bench/labs/pairwhere.py --opcode=216 bench/bench.py

Used on the fused LOAD_SMALL_INT pair it found exactly one head, in bench.py's
`bench_call` inner loop, which is where the +0.4% on the `function call` case came
from - one dispatch out of about eight, against a callee costing ~300 ns.
"""

import sys

HEAD = 216


def parse(argv):
    global HEAD
    if argv and argv[0].startswith("--opcode="):
        HEAD = int(argv.pop(0).split("=", 1)[1])
    return argv


def opcode_units(code):
    raw = code.co_code
    return [raw[i] for i in range(0, len(raw), 2)]


def walk(code, path):
    here = f"{path}/{code.co_name}@{code.co_firstlineno}"
    positions = [i for i, op in enumerate(opcode_units(code)) if op == HEAD]
    if positions:
        print(f"{here} units={len(opcode_units(code))} heads={positions}")
    for constant in code.co_consts:
        if type(constant).__name__ == "code":
            walk(constant, here)


for path in parse(sys.argv[1:]):
    with open(path, "rb") as source:
        walk(compile(source.read(), path, "exec"), path)
