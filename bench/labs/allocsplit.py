import sys, time
N = 200_000
REPS = 7
# literal form builds the object with one bytecode instruction and no call;
# the call form adds a builtin call. The difference isolates allocation.
def loop_lit_tuple():
    for _ in range(N):
        ()
def loop_lit_list():
    for _ in range(N):
        []
def loop_lit_dict():
    for _ in range(N):
        {}
def loop_lit_set():
    for _ in range(N):
        {1}
def loop_lit_str_concat():
    s = "abcdefgh"
    for _ in range(N):
        s + "ij"
def loop_lit_bytes():
    for _ in range(N):
        b""
def loop_call_tuple():
    f = tuple
    for _ in range(N):
        f()
def loop_call_list():
    f = list
    for _ in range(N):
        f()
def loop_call_dict():
    f = dict
    for _ in range(N):
        f()
def loop_call_bytes():
    f = bytes
    for _ in range(N):
        f()
def loop_fresh_exception_no_raise():
    e = ValueError
    for _ in range(N):
        e(1)
def loop_str_upper():
    s = "abcdefgh"
    up = s.upper
    for _ in range(N):
        up()
CASES = [("() literal", loop_lit_tuple), ("tuple() call", loop_call_tuple),
         ("[] literal", loop_lit_list), ("list() call", loop_call_list),
         ("{} literal", loop_lit_dict), ("dict() call", loop_call_dict),
         ("b'' literal", loop_lit_bytes), ("bytes() call", loop_call_bytes),
         ("{1} literal", loop_lit_set), ("s+ij literal", loop_lit_str_concat),
         ("s.upper()", loop_str_upper), ("ValueError(1)", loop_fresh_exception_no_raise)]
print("==", sys.version.split()[0])
for label, fn in CASES:
    fn()
    best = None
    for _ in range(REPS):
        t0 = time.perf_counter(); fn(); dt = time.perf_counter() - t0
        ns = dt * 1e9 / N
        best = ns if best is None or ns < best else best
    print(f"{label:22s} {best:9.1f} ns/iter")
