"""Where does a builtin method call's time go: the call site or the result alloc?

Every row is the same shape - LOAD_ATTR(method) + CALL with no arguments - so the
difference between two rows is the kernel body plus whatever the returned object
costs to create: a bool answer allocates nothing, a str answer allocates the
result, `hash` returns a small int.

    python bench/labs/callsite.py
"""
import timeit

N = 200_000
s = "abcdefgh"

SHAPES = [
    ("nothing", lambda: None),
    ("isascii -> bool", lambda: s.isascii()),
    ("islower -> bool", lambda: s.islower()),
    ("hash -> small int", lambda: hash(s)),
    ("len -> small int", lambda: len(s)),
    ("upper -> str", lambda: s.upper()),
    ("capitalize -> str", lambda: s.capitalize()),
    ("swapcase -> str", lambda: s.swapcase()),
    ("encode -> bytes", lambda: s.encode()),
]

for name, fn in SHAPES:
    best = min(timeit.repeat(fn, number=N, repeat=3))
    print(f"{name:22s} {best / N * 1e9:7.1f} ns/iter")

# Is the cost the builtin-method path, or the shared LOAD_METHOD + CALL pair?
class C:
    def zero(self):
        return 0

    def one(self, a):
        return a


c = C()
PAIR = [
    ("lambda baseline", lambda: None),
    ("c.zero() user method, no args", lambda: c.zero()),
    ("c.one(1) user method, one arg", lambda: c.one(1)),
    ("s.isascii() builtin, no args", lambda: s.isascii()),
    ("d.get('k') builtin, one arg", lambda: {}.get("k")),
]
for name, fn in PAIR:
    best = min(timeit.repeat(fn, number=N, repeat=3))
    print(f"{name:34s} {best / N * 1e9:7.1f} ns/iter")
