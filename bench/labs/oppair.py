"""Which instruction pairs actually execute, and how often they are adjacent.

Run a workload under `f_trace_opcodes` and tally every consecutive pair of
executed instructions that sit next to each other in the same code object, so
the output ranks the fusion candidates in the order that would pay. Adjacency is
measured in code offsets (a unit is 2 bytes, and an opcode with inline caches is
followed by its cache units), so a pair counts only when the second instruction
really follows the first.

    python oppair.py <script.py> [max-events]

The tracer makes the workload tens of times slower; the cap bounds the sample.
Specialized opcodes show up as themselves, which is what the interpreter runs.
"""

import collections
import dis
import sys
import time

MAX_EVENTS = int(sys.argv[2]) if len(sys.argv) > 2 else 300_000
target = sys.argv[1]

# offset -> opcode name, per code object, cached
_names = {}


_rebuilt = set()


def name_of(code, offset):
    table = _names.get(id(code))
    if table is None or (offset not in table and (id(code), offset) not in _rebuilt):
        # Adaptive specialization rewrites the units while the workload runs, so
        # a table decoded before a site specialized is stale: rebuild once per
        # code object for each offset that is missing from it.
        _rebuilt.add((id(code), offset))
        table = {}
        for instr in dis.get_instructions(code):
            if instr.offset is not None:
                table[instr.offset] = instr.opname
        _names[id(code)] = table
    return table.get(offset, "?")


pairs = collections.Counter()
deltas = collections.defaultdict(collections.Counter)
ops = collections.Counter()
prev = None
events = 0
truncated = False


def tracer(frame, event, arg):
    global prev, events, truncated
    if event == "call":
        frame.f_trace_opcodes = True
    elif event == "opcode":
        events += 1
        if events > MAX_EVENTS:
            truncated = True
            sys.settrace(None)
            return None
        code = frame.f_code
        # f_lasti is the byte offset of the *next* unit (2 * (index + 1)),
        # CPython's prev_instr convention, so the running instruction sits two
        # bytes before it.
        offset = frame.f_lasti - 2
        key = (id(code), offset)
        ops[name_of(code, offset)] += 1
        if prev is not None and prev[0] == key[0]:
            delta = offset - prev[1]
            first = name_of(code, prev[1])
            second = name_of(code, offset)
            pairs[(first, second, delta)] += 1
            deltas[(first, second)][delta] += 1
        prev = key
    return tracer


code = compile(open(target, encoding="utf-8").read(), target, "exec")
sys.settrace(tracer)
started = time.perf_counter()
try:
    exec(code, {"__name__": "__main__", "__file__": target})
except SystemExit:
    pass
except BaseException as exc:  # the workload may fail; the sample still counts
    print("!! workload raised", type(exc).__name__, exc, file=sys.stderr)
finally:
    sys.settrace(None)

elapsed = time.perf_counter() - started
print(f"sampled {events} instruction events in {elapsed:.1f}s (truncated={truncated})")
print("\n=== top opcode alone ===")
for name, count in ops.most_common(20):
    print(f"{count:9d}  {100.0 * count / max(events, 1):5.1f}%  {name}")
print("\n=== top adjacent pairs ===")
for (first, second, delta), count in pairs.most_common(30):
    share = 100.0 * count / max(events, 1)
    print(f"{count:9d}  {share:5.1f}%  +{delta:3d}  {first} -> {second}")
