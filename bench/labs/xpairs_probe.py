"""throwaway probe: rank adjacent opcode pairs by loop-body membership.

pairrank.py execs bench.py (which runs its timed driver), so this probe only
compiles it: `compile()` already gives every nested code object, so the whole
file can be scanned without executing a single benchmark case. For each pair it
reports how many times it occurs at all, how many of those sit inside a loop
body (once per iteration), and which function holds each occurrence.
"""

import dis
import sys

PATH = sys.argv[1] if len(sys.argv) > 1 else "bench/bench.py"
DUMP = sys.argv[2] if len(sys.argv) > 2 else ""

src = open(PATH, encoding="utf-8").read()
# Drop the driver so compiling never runs it.
head = src.split('\nprint(f"=== benchmark')[0]
head = head.split("\nif __name__")[0]
module = compile(head, PATH, "exec")

SKIP = ("CACHE", "EXTENDED_ARG")


def codes(node, path="", out=None):
    out = [] if out is None else out
    here = f"{path}/{node.co_name}@{node.co_firstlineno}"
    out.append((here, node))
    for const in node.co_consts:
        if type(const).__name__ == "code":
            codes(const, here, out)
    return out


def flat(c):
    """(index, instr) for real instructions, and offset -> index."""
    instrs = [i for i in dis.get_instructions(c) if not i.opname.startswith(SKIP)]
    index = {i.offset: n for n, i in enumerate(instrs)}
    return instrs, index


def jump_target(instr, next_offset):
    """CPython convention: forward +, backward -, arg counts 2-byte units."""
    if instr.arg is None:
        return None
    delta = instr.arg * 2
    if "BACKWARD" in instr.opname:
        return next_offset - delta
    return next_offset + delta


def loop_regions(c):
    """[(lo, hi)] byte-offset ranges that a loop body re-executes."""
    instrs, index = flat(c)
    regions = []
    for n, i in enumerate(instrs):
        nxt = instrs[n + 1].offset if n + 1 < len(instrs) else len(c.co_code)
        t = jump_target(i, nxt)
        if t is None:
            continue
        if "BACKWARD" in i.opname and t < i.offset:
            regions.append((t, nxt))
        elif i.opname in ("FOR_ITER", "SEND") and t > i.offset:
            # body is everything after FOR_ITER up to its exit target
            regions.append((nxt, t))
    return regions


pairs_all = {}
pairs_loop = {}
sites = {}

for where, c in codes(module):
    instrs, index = flat(c)
    regions = loop_regions(c)
    names = [i.opname for i in instrs]
    for n, (a, b) in enumerate(zip(names, names[1:])):
        key = (a, b)
        pairs_all[key] = pairs_all.get(key, 0) + 1
        off = instrs[n].offset
        inside = [r for r in regions if r[0] <= off < r[1]]
        if inside:
            pairs_loop[key] = pairs_loop.get(key, 0) + 1
            sites.setdefault(key, []).append(
                f"{where}+{off} depth={len(inside)}"
            )

print(f"{PATH}: code objects scanned={len(codes(module))}")
print(f"{'pair':44s} {'all':>5s} {'in-loop':>8s}")
for key, n in sorted(pairs_all.items(), key=lambda kv: (-pairs_loop.get(kv[0], 0), -kv[1]))[:30]:
    print(f"{key[0] + ' -> ' + key[1]:44s} {n:5d} {pairs_loop.get(key, 0):8d}")

print("\nsites of the top in-loop pairs:")
for key, _ in sorted(pairs_loop.items(), key=lambda kv: -kv[1])[:12]:
    print(f"  {key[0]} -> {key[1]}: " + "; ".join(sites[key][:6]))

if DUMP:
    print(f"\n=== dump of {DUMP} ===")
    for where, c in codes(module):
        if c.co_name == DUMP:
            instrs, _ = flat(c)
            regions = loop_regions(c)
            for i in instrs:
                tag = "  <loop" if any(r[0] <= i.offset < r[1] for r in regions) else ""
                print(f"  {where} {i.offset:4d} {i.opname:26s} {i.arg}{tag}")
