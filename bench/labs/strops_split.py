"""bench.py's `string ops` case (bench_str, bench.py lines 69-73), split per op.

Same loop shape, same data ("abcdefgh" + "ij"), best-of-N time.perf_counter.
All locals are bound inside the function so the bytecode shape matches
bench.py (LOAD_FAST for `s`, not LOAD_GLOBAL).

    rustpython bench/labs/strops_split.py
    python     bench/labs/strops_split.py

Measured on rp-lite-113 vs cp314 (best of 5 over 200k, ns/op; "net" subtracts
each side's own empty-loop control, 30.0 RP / 15.5 CP):

    op                     RP net   CP net
    t = s.upper   (attr)    142.5     33.0
    t = s2.split  (attr)    142.8     33.6
    s.upper()                89.7     21.8
    u()  hoisted bound      129.9     25.0
    up(s) unbound           128.3     21.1
    s2.split('d')           275.7     39.1
    s2.split()              237.0     34.2
    whole bench case        467.0    106.7

Scoped gates on the same binary (`LUNA_STUB_STR=ABCDEFGHIJ`, control row
included in each): everything the `split` kernel does past argument binding is
113.8 ns (`splbind` 171.3 vs base 285.1), and building the one piece inside it
is 67.5 ns (`splpiece` 217.6).

The separator here never occurs ("d" is lowercase, "ABCDEFGHIJ" is not), so
`s2.split("d")` is the no-match shape, and the gates in `perf_debug.rs` that
price inside it (`splbind`, `splpiece`, `spscan`, `spnode`) only fire for
subjects matching LUNA_STUB_STR. Without that variable set they are no-ops and
every row prints unchanged, which is how a "measured zero" was once mistaken for
an answer:

    LUNA_STUB_STR=ABCDEFGHIJ LUNA_ABLATE=splpiece rustpython bench/labs/strops_split.py
"""
import sys
import time

N = 200_000
REPEAT = 5


def control(n):
    # empty loop with the same accumulator store, so loop + store cost subtracts
    s = "abcdefgh"
    for _ in range(n):
        t = s


def upper_only(n):
    s = "abcdefgh"
    for _ in range(n):
        t = s.upper()


def concat_only(n):
    u = "ABCDEFGH"
    for _ in range(n):
        t = u + "ij"


def upper_plus_concat(n):
    s = "abcdefgh"
    for _ in range(n):
        t = s.upper() + "ij"


def split_only(n):
    s2 = "ABCDEFGHIJ"
    for _ in range(n):
        t = s2.split("d")


def split_noarg(n):
    s2 = "ABCDEFGHIJ"
    for _ in range(n):
        t = s2.split()


def whole_case(n):
    s = "abcdefgh"
    for _ in range(n):
        s2 = s.upper() + "ij"
        s2.split("d")


def attr_only_upper(n):
    # LOAD_ATTR of a builtin method: prices bound-method creation, no call
    s = "abcdefgh"
    for _ in range(n):
        t = s.upper


def unbound_upper(n):
    up = str.upper
    s = "abcdefgh"
    for _ in range(n):
        t = up(s)


def hoisted_upper(n):
    u = "abcdefgh".upper
    for _ in range(n):
        t = u()


def attr_only_split(n):
    s2 = "ABCDEFGHIJ"
    for _ in range(n):
        t = s2.split


def unbound_split(n):
    sp = str.split
    s2 = "ABCDEFGHIJ"
    for _ in range(n):
        t = sp(s2, "d")


def upper_long(n):
    # 64 chars: prices the per-character work separately
    s = "abcdefgh" * 8
    for _ in range(n):
        t = s.upper()


def split_long(n):
    s2 = ("abcdefgh" * 8).upper() + "DEFGHIJKL"
    for _ in range(n):
        t = s2.split("D")


CASES = [
    ("control: loop+store", control),
    ("s.upper()", upper_only),
    ("u + 'ij'", concat_only),
    ("s.upper() + 'ij'", upper_plus_concat),
    ("s2.split('d')", split_only),
    ("s2.split()", split_noarg),
    ("whole bench case", whole_case),
    ("t = s.upper (attr)", attr_only_upper),
    ("str.upper(s) unbound", unbound_upper),
    ("hoisted u()", hoisted_upper),
    ("t = s2.split (attr)", attr_only_split),
    ("str.split(s2,'d')", unbound_split),
    ("upper 64 chars", upper_long),
    ("split('D') 73 chars", split_long),
]

print("=== %s py%s ===" % (sys.implementation.name, sys.version.split()[0]))
for name, fn in CASES:
    best = None
    for _ in range(REPEAT):
        t0 = time.perf_counter()
        fn(N)
        dt = time.perf_counter() - t0
        if best is None or dt < best:
            best = dt
    ns = best / N * 1e9
    print("%-22s %9.3f M ops/s %9.1f ns/op" % (name, 1e3 / ns, ns))
