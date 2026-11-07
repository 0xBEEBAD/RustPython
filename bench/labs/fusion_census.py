"""Count candidate instruction pairs in a script's final bytecode.

Every dispatch-removing fusion has to beat the work it adds to codegen, so the
first question is a count, not a measurement: how many times does the pair
actually appear, and is it inside something that runs repeatedly? This walks the
compiled code objects of a script (no execution), skips inline-cache rows, and
reports each adjacent pair of interest with the code object that holds it and
that object's own loop count, which is what tells a loop-body pair from a
module-body pair.

    bench/labs/variants/rp-lite-119.exe bench/labs/fusion_census.py bench/bench.py
    bench/labs/cp314/python.exe         bench/labs/fusion_census.py bench/bench.py

Pairs are the ones task #94 ranked: STORE_FAST followed by LOAD_GLOBAL is the
broad candidate; LOAD_GLOBAL followed by LOAD_SMALL_INT and LOAD_CONST followed
by STORE_FAST are the narrow ones listed there for contrast.

Measured 2026-11-07 over bench/bench.py + bench/async1.py, with IDENTICAL totals
from both interpreters - which is also the evidence that the synced opcode.py
cache table walks our co_code correctly: STORE_FAST>LOAD_GLOBAL 19,
LOAD_GLOBAL>STORE_FAST 0, LOAD_CONST>STORE_FAST 2, STORE_FAST>LOAD_FAST 0
(already fused), FOR_ITER>STORE_FAST 14. Thirteen of the 19 are in bench.py and
every code object that has one also contains a FOR_ITER, so they are
per-iteration; async1's six sit in `main`, which has no loop, so they run once.
Task #94 records why this still may not be worth building: LOAD_GLOBAL
specializes in place, and the retained-unit fusion convention would skip that.
"""

import dis
import sys

# (name, first opname, second opname)
PAIRS = [
    ("STORE_FAST>LOAD_GLOBAL", "STORE_FAST", "LOAD_GLOBAL"),
    ("LOAD_GLOBAL>STORE_FAST", "LOAD_GLOBAL", "STORE_FAST"),
    ("LOAD_CONST>STORE_FAST", "LOAD_CONST", "STORE_FAST"),
    ("STORE_FAST>LOAD_FAST", "STORE_FAST", "LOAD_FAST"),
    ("FOR_ITER>STORE_FAST", "FOR_ITER", "STORE_FAST"),
]

# Runs of three. A fusion is only worth building if it removes more than one
# dispatch, because the fused arm still pays a branch, an arg read and a skip
# calculation on top of both bodies - so a two-unit candidate has to clear that
# against one saved dispatch, while a three-unit candidate clears it against two.
TRIPLES = [
    ("FOR_ITER>STORE_FAST>LOAD_GLOBAL", ("FOR_ITER", "STORE_FAST", "LOAD_GLOBAL")),
    ("LOAD_GLOBAL>LOAD_CONST>CALL", ("LOAD_GLOBAL", "LOAD_CONST", "CALL")),
    ("LOAD_CONST>LOAD_CONST>CALL", ("LOAD_CONST", "LOAD_CONST", "CALL")),
    ("LOAD_FAST>LOAD_FAST>BINARY_OP", ("LOAD_FAST", "LOAD_FAST", "BINARY_OP")),
    ("CALL>POP_TOP>JUMP_BACKWARD", ("CALL", "POP_TOP", "JUMP_BACKWARD")),
    ("LOAD_GLOBAL>LOAD_FAST>CALL", ("LOAD_GLOBAL", "LOAD_FAST", "CALL")),
    ("BINARY_OP>STORE_FAST>LOAD_FAST", ("BINARY_OP", "STORE_FAST", "LOAD_FAST")),
    ("LOAD_CONST>STORE_FAST>LOAD_GLOBAL", ("LOAD_CONST", "STORE_FAST", "LOAD_GLOBAL")),
]


def count_runs(seq, wanted):
    hits = 0
    n = len(wanted)
    for i in range(len(seq) - n + 1):
        if tuple(seq[i:i + n]) == wanted:
            hits += 1
    return hits


SKIP = {"CACHE", "EXTENDED_ARG"}


def walk(code, seen):
    yield code
    for const in code.co_consts:
        if hasattr(const, "co_code") and id(const) not in seen:
            seen.add(id(const))
            yield from walk(const, seen)


def instrs(code):
    out = []
    for i in dis.get_instructions(code):
        if i.opname in SKIP:
            continue
        out.append(i.opname)
    return out


def main(argv):
    if not argv:
        print("usage: fusion_census.py <script.py> [...]")
        return 1
    totals = dict((name, 0) for name, _, _ in PAIRS)
    totals.update((name, 0) for name, _ in TRIPLES)
    per_code = []
    for path in argv:
        with open(path, "r", encoding="utf-8") as fp:
            source = fp.read()
        code = compile(source, path, "exec")
        for obj in walk(code, {id(code)}):
            seq = instrs(obj)
            loops = seq.count("FOR_ITER") + seq.count("GET_ITER")
            for name, first, second in PAIRS:
                hits = 0
                for i in range(len(seq) - 1):
                    if seq[i] == first and seq[i + 1] == second:
                        hits += 1
                if hits:
                    totals[name] += hits
                    per_code.append((path, obj.co_name, hits, name, loops))
            for name, wanted in TRIPLES:
                hits = count_runs(seq, wanted)
                if hits:
                    totals[name] += hits
                    per_code.append((path, obj.co_name, hits, name, loops))
    print("== totals over %d file(s) ==" % len(argv))
    for name, _, _ in PAIRS:
        print("%-34s %d" % (name, totals[name]))
    print("-- three-unit runs (these remove two dispatches) --")
    for name, _ in TRIPLES:
        print("%-34s %d" % (name, totals[name]))
    print("== where they are (file, code object, hits, pair, loops in that object) ==")
    for row in sorted(per_code, key=lambda r: (-r[2], -r[4]))[:25]:
        print("  %s" % (row,))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
