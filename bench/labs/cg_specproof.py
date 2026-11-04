"""cg_specproof.py - does LOAD_GLOBAL actually specialize to LoadGlobalModule/Builtin?

co_code is original_bytes() (pre-specialization). _co_code_adaptive is the live
instruction stream. Diff them around the LOAD_GLOBAL unit before and after
running the loop, which proves which arm executes at steady state.
"""


def f(a):
    return a


def lg(n):
    i = 0
    while i < n:
        f(1)
        i += 1


def dump(tag, co):
    live = co._co_code_adaptive
    orig = co.co_code
    # find the LOAD_GLOBAL opcode byte (102 in CPython numbering; print raw bytes)
    print(f"{tag}: identical={bytes(live) == bytes(orig)}")
    diffs = [(k, orig[k], live[k]) for k in range(min(len(orig), len(live)))
             if orig[k] != live[k]]
    print(f"{tag}: differing unit bytes {diffs[:12]}")


dump("before", lg.__code__)
lg(30000)
dump("after ", lg.__code__)

# opcode numbers in this tree
import sys
print("max opcode-ish:", sys.maxsize > 2**32)
print("lg.co_stacksize", lg.__code__.co_stacksize)
