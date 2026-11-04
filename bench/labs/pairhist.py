"""Which instruction pairs actually EXECUTE in bench.py's cases, and how often.

Static adjacency (pairrank.py) is not the prize - a pair inside a loop body runs
once per iteration. `sys.monitoring` INSTRUCTION events give the executed
sequence, so count adjacent pairs and multiply by the measured ~8 ns dispatch
cost to rank what a fusion is worth. The callback is Python, so keep N small.
"""
import dis
import sys
from collections import Counter

mon = sys.monitoring
TOOL = mon.PROFILER_ID
mon.use_tool_id(TOOL, "pairhist")

names_by_code = {}
targets = set()


def name_of(code, offset):
    table = names_by_code.get(code)
    if table is None:
        table = {i.offset: i.opname for i in dis.get_instructions(code)}
        names_by_code[code] = table
    return table.get(offset, "?")


last = [(None, None)]


def on_instr(code, offset):
    if code not in targets:
        # The callback's own instructions arrive here; dropping them without
        # touching `last` keeps the target sequence contiguous.
        return
    op = name_of(code, offset)
    prev_code, prev_op = last[0]
    # Only pairs inside one code object: a call crosses functions, and that
    # boundary is the frame machinery's cost, not a dispatch pair.
    if prev_code is code and prev_op is not None:
        pairs[(prev_op, op)] += 1
    last[0] = (code, op)


pairs = Counter()
runs = Counter()

with open("bench/bench.py", encoding="utf-8") as f:
    src = f.read()
head = src.split('\nprint(f"=== benchmark')[0]
head = head.split("\nif __name__")[0]
env = {}
exec(compile(head, "bench/bench.py", "exec"), env)

N = 60
cases = {k: v for k, v in env.items() if k.startswith("bench_") and callable(v)}
# helpers the cases call into are interesting too (throw(), f(), C.__init__...)
for value in list(env.values()):
    if callable(value) and getattr(value, "__code__", None) is not None:
        targets.add(value.__code__)
    for sub in getattr(value, "__dict__", {}).values():
        if callable(sub) and getattr(sub, "__code__", None) is not None:
            targets.add(sub.__code__)

mon.register_callback(TOOL, mon.events.INSTRUCTION, on_instr)
# Build the offset -> opname tables BEFORE turning the tool on: once a code
# object is instrumented, dis reports INSTRUMENTED_INSTRUCTION for every offset.
for code in targets:
    name_of(code, 0)
mon.set_events(TOOL, mon.events.INSTRUCTION)
try:
    for name, fn in cases.items():
        last[0] = (None, None)
        runs[name] = N
        fn(N)
finally:
    mon.set_events(TOOL, mon.events.NO_EVENTS)
    mon.free_tool_id(TOOL)

total_iters = sum(runs.values()) * N
print(f"cases={len(cases)} iterations={total_iters}")
print(f"{'executed pair':42s} {'per-iter':>9s}")
for (a, b), n in pairs.most_common(18):
    print(f"{a + ' -> ' + b:42s} {n / total_iters:9.2f}")

print()
print("executed opcode frequency:")
ops = Counter()
for (a, b), n in pairs.items():
    ops[b] += n
for name, n in ops.most_common(12):
    print(f"{name:24s} {n / total_iters:9.2f}")
