"""Cost of extracting an int argument in a native builtin method.

Same loop shape as bench/labs/strarg_probe.py, best-of-REPEAT over N, prints its
own loop+store control so the floor subtracted is from THIS run.

Why these rows: `split(sep, 0)` vs `split(sep)` is CONFOUNDED - anystr.rs:193
branches on `maxsplit < 0` into a different kernel (`split` vs `splitn`), so
that delta is mostly the other kernel, not the argument. The rows below are
chosen so the Rust kernel is identical across a pair and the delta is the
argument alone:

  A) isize path (SplitArgs / ReplaceArgs, `#[pyarg(any, default = -1)] x: isize`)
     split('z') and split('z', -1) both take `if maxsplit < 0 => split()`.
     replace('q','r') and replace('q','r',-1) both take Ordering::Less.

  B) Option<PyIntRef> path (FindArgs) at a kernel that never branches on it:
     count/find always call adjust_indices and scan the same 0..len range, so
        count('z')        -> no index slot at all
        count('z', None)  -> +1 arg slot, is_none() short-circuit, no int work
        count('z', 0)     -> +1 arg slot, PyIntRef extract + to_isize()
     (None - baseline) is the plumbing; (0 - None) is the integer.

  C) startswith = B plus a real slice (get_value -> char_range_to_bytes ->
     &Wtf8[range]), which split and count never do.

  D) an object with __index__ only (parity probe; raises on RustPython).

    ./bench/labs/variants/rp-lite-114.exe bench/labs/ia_argcost.py
    ./bench/labs/cp314/python.exe         bench/labs/ia_argcost.py
"""
import sys
import time

N = 200_000
REPEAT = 5

BIG70 = 2 ** 70  # > isize::MAX: PyIntRef paths saturate, isize path raises


class Indexed:
    def __index__(self):
        return 0


IDX = Indexed()
M1 = -1
CONSTS = {"BIG70": BIG70, "IDX": IDX, "M1": M1}

ROWS = [
    ("ctrl loop+store", 's'),
    # --- A: isize extraction, kernel identical across the pair --------------
    ("A split('z')       [1 arg]", 's.split("z")'),
    ("A split('z',-1)    [isize]", 's.split("z", -1)'),
    ("A split('z',M1)    [isize]", 's.split("z", M1)'),
    ("A replace 2-arg no-int", 's.replace("q","r")'),
    ("A replace 3-arg -1", 's.replace("q","r", -1)'),
    ("A replace 3-arg 0 (other kernel)", 's.replace("q","r", 0)'),
    # --- B: Option<PyIntRef>, kernel never branches on the arg -------------
    ("B count('z')       [1 arg]", 's.count("z")'),
    ("B count('z',None)  [slot only]", 's.count("z", None)'),
    ("B count('z',0)     [slot+int]", 's.count("z", 0)'),
    ("B count('z',None,None)", 's.count("z", None, None)'),
    ("B count('z',0,8)   [2 int]", 's.count("z", 0, 8)'),
    ("B count('z',2**70) [saturate]", 's.count("z", BIG70)'),
    ("B find('z')        [1 arg]", 's.find("z")'),
    ("B find('z',None)   [slot only]", 's.find("z", None)'),
    ("B find('z',0)      [slot+int]", 's.find("z", 0)'),
    ("B find('z',0,8)    [2 int]", 's.find("z", 0, 8)'),
    ("B find('z',2**70)  [saturate]", 's.find("z", BIG70)'),
    # --- C: startswith = B + a real slice ----------------------------------
    ("C startswith('abc')[1 arg]", 's.startswith("abc")'),
    ("C sw(..,None)      [slot only]", 's.startswith("abc", None)'),
    ("C sw(..,0)         [slot+int]", 's.startswith("abc", 0)'),
    ("C sw(..,0,8)       [2 int]", 's.startswith("abc", 0, 8)'),
    ("C sw(..,2**70)     [saturate]", 's.startswith("abc", BIG70)'),
    # --- D: __index__ only --------------------------------------------------
    ("D count('z',Idx())", 's.count("z", IDX)'),
    ("D sw(..,Idx())", 's.startswith("abc", IDX)'),
    # --- E: isize ladder on a kernel that ignores the value when it equals
    #     the default, so the only variable is the extraction.
    #     ExpandTabsArgs{tabsize: isize, default = 8}: "abcdefgh" has no tab,
    #     so tabsize 8 and the default produce the same output and same loop.
    ("E expandtabs()      [1 arg]", 's.expandtabs()'),
    ("E expandtabs(8)     [isize]", 's.expandtabs(8)'),
    ("E expandtabs(2**70) [bignum]", 's.expandtabs(BIG70)'),
    ("E expandtabs(True)  [bool ]", 's.expandtabs(True)'),
    #     SplitLinesArgs{keepends: bool, default = false} - the non-int sibling
    ("E splitlines()      [1 arg 0]", 's.splitlines()'),
    ("E splitlines(False) [bool ]", 's.splitlines(False)'),
    # --- F: same slot, keyword instead of positional ------------------------
    ("F split kw maxsplit=-1", 's.split("z", maxsplit=-1)'),
    ("F split kw sep+maxsplit", 's.split(sep="z", maxsplit=-1)'),
    ("F replace kw count=-1", 's.replace("q","r", count=-1)'),
]

fns = []
for name, expr in ROWS:
    ns = dict(CONSTS)
    exec("def f(s, n):\n    for _ in range(n):\n        t = %s\n" % expr, ns)
    fns.append((name, ns["f"]))

print("=== %s py%s ===" % (sys.implementation.name, sys.version.split()[0]))
print("N=%d best-of-%d" % (N, REPEAT))
results = []
for name, fn in fns:
    s = "abcdefgh"
    best = None
    err = None
    for _ in range(REPEAT):
        try:
            t0 = time.perf_counter()
            fn(s, N)
            dt = time.perf_counter() - t0
        except Exception as e:
            err = "%s: %s" % (type(e).__name__, e)
            break
        if best is None or dt < best:
            best = dt
    if err is not None:
        results.append((name, None))
        print("%-33s  ERROR %s" % (name, err))
    else:
        val = best / N * 1e9
        results.append((name, val))
        print("%-33s %9.1f ns" % (name, val))

base = next(v for k, v in results if k.startswith("ctrl"))
print("\n--- nets over THIS run's ctrl (%.1f ns) ---" % base)
for k, v in results:
    if v is not None and not k.startswith("ctrl"):
        print("%-33s %9.1f ns" % (k, v - base))
