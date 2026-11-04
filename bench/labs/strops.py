"""bench.py's `string ops` case, split into its parts.

    python bench/labs/strops.py
"""
import timeit

N = 300_000
s = "abcdefgh"


def whole(n):
    for _ in range(n):
        s2 = s.upper() + "ij"
        s2.split("d")


def upper_only(n):
    for _ in range(n):
        s.upper()


def upper_add(n):
    for _ in range(n):
        s2 = s.upper() + "ij"


def split_only(n):
    s2 = s.upper() + "ij"
    for _ in range(n):
        s2.split("d")


def concat_only(n):
    u = s.upper()
    for _ in range(n):
        u + "ij"


def loop_only(n):
    for _ in range(n):
        pass


for name, fn in [
    ("loop only", loop_only),
    ("whole bench case", whole),
    ("s.upper()", upper_only),
    ("s.upper() + 'ij'", upper_add),
    ("u + 'ij' only", concat_only),
    ("s2.split('d') only", split_only),
]:
    best = min(timeit.repeat(lambda: fn(N), number=1, repeat=5))
    print(f"{name:24s} {best / N * 1e9:7.1f} ns/iter")

# Where does the per-call time go: attribute load (bound method creation), the
# argument conversion, or the result collection?
def bound_hoisted(n):
    m = s2 = s.upper()
    f = m.split
    for _ in range(n):
        f("d")


def unbound(n):
    sp = str.split
    s2 = s.upper() + "ij"
    for _ in range(n):
        sp(s2, "d")


def upper_hoisted(n):
    u = s.upper
    for _ in range(n):
        u()


def split_noarg(n):
    s2 = s.upper() + "ij"
    for _ in range(n):
        s2.split()


for name, fn in [
    ("split attr hoisted", split_hoisted if False else bound_hoisted),
    ("str.split(s2,'d') unbound", unbound),
    ("s.upper attr hoisted", upper_hoisted),
    ("s2.split() no separator", split_noarg),
]:
    best = min(timeit.repeat(lambda: fn(N), number=1, repeat=5))
    print(f"{name:28s} {best / N * 1e9:7.1f} ns/iter")
