"""Which adjacent opcode pairs actually run in bench.py's hot functions?

A fusion only pays if the pair is hot, so rank the pairs by how often they occur
in the compiled bodies of the benchmark cases, weighted by the number of times the
function executes its loop body (one pair per iteration for pairs inside the loop).
"""
import dis
import importlib.util
import sys
from collections import Counter

with open("bench/bench.py", encoding="utf-8") as f:
    src = f.read()
# bench.py runs its cases at import time; keep only the definitions.
head = src.split("\ndef main(")[0] if "\ndef main(" in src else src
head = head.split("\nif __name__")[0]
bench = {}
exec(compile(head, "bench/bench.py", "exec"), bench)

funcs = [v for k, v in bench.items() if k.startswith("bench_") and callable(v)]
pairs = Counter()
for fn in funcs:
    code = fn.__code__
    instrs = [i for i in dis.get_instructions(code) if not i.opname.startswith(("CACHE", "EXTENDED"))]
    names = [i.opname for i in instrs]
    for a, b in zip(names, names[1:]):
        pairs[(a, b)] += 1

print("cases:", len(funcs))
print(f"{'pair':44s} {'count':>6s}")
for (a, b), n in pairs.most_common(25):
    print(f"{a + ' -> ' + b:44s} {n:6d}")

print()
print("top single opcodes:")
opcodes = Counter()
for fn in funcs:
    for i in dis.get_instructions(fn.__code__):
        if not i.opname.startswith(("CACHE", "EXTENDED")):
            opcodes[i.opname] += 1
for name, n in opcodes.most_common(15):
    print(f"{name:24s} {n:6d}")
