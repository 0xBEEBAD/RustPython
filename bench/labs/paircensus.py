"""Static census of how often a codegen fusion actually fires in a script.

Every dispatch-removing fusion has to beat the cost of the unit it swallows, so
before measuring one, count it and ask how often those units run. Two numbers
decide the ceiling: this census (how many heads, and pairwhere.py says whether
they sit in a hot loop) and the measured 6.2 ns dispatch against the work the
surrounding unit does. A pair of literal call arguments fuses one dispatch out of
about eight in the loop, but the call itself costs ~300 ns, so the shape cannot
pay for itself even when it fires on every iteration.

    target/release/rustpython.exe bench/labs/paircensus.py --opcode=216 bench/bench.py

The default opcode is the fused LOAD_SMALL_INT pair (216), measured at 1 head in
1266 units on bench/bench.py and 0 on async1.py, django1.py and imports.py, then
deleted: +0.2% geomean and +0.4% on the one case it touches, inside the +-2.4%
band that cases it cannot touch swung by.
"""

import sys

HEAD = 216
PLAIN = 94  # LOAD_SMALL_INT, the unit a pair head replaces


def parse(argv):
    global HEAD
    if argv and argv[0].startswith("--opcode="):
        HEAD = int(argv.pop(0).split("=", 1)[1])
    return argv


def opcode_units(code):
    raw = code.co_code
    return [raw[i] for i in range(0, len(raw), 2)]


def walk(code, tally):
    for op in opcode_units(code):
        tally[op] = tally.get(op, 0) + 1
    for constant in code.co_consts:
        if type(constant).__name__ == "code":
            walk(constant, tally)


for path in parse(sys.argv[1:]):
    with open(path, "rb") as source:
        code = compile(source.read(), path, "exec")
    tally = {}
    walk(code, tally)
    heads = tally.get(HEAD, 0)
    total = sum(tally.values())
    print(
        f"{path:26s} opcode={HEAD:3d} heads={heads:6d} plain(94)={tally.get(PLAIN, 0):6d} "
        f"of {total:8d} units ({100.0 * heads / max(total, 1):.2f}%)"
    )
