import sys, time
N = 200_000
REPS = 7
class Plain:
    pass
def loop_tuple():
    for _ in range(N):
        ()
def loop_empty_tuple_call():
    t = tuple
    for _ in range(N):
        t()
def loop_list_new():
    l = list
    for _ in range(N):
        l()
def loop_dict_new():
    d = dict
    for _ in range(N):
        d()
def loop_valueerror():
    e = ValueError
    for _ in range(N):
        e(1)
def loop_valueerror_noargs():
    e = ValueError
    for _ in range(N):
        e()
def loop_plain_instance():
    c = Plain
    for _ in range(N):
        c()
def loop_lambda():
    for _ in range(N):
        (lambda: 0)
def loop_int_from_int():
    i = int
    for _ in range(N):
        i(7)
def loop_bytes_new():
    b = bytes
    for _ in range(N):
        b()
def loop_range_new():
    r = range
    for _ in range(N):
        r(2)
def loop_cell():
    c = lambda: 0
    cl = type((lambda x: (lambda: x))(0))
    for _ in range(N):
        cl(1)
CASES = [("tuple()", loop_empty_tuple_call), ("list()", loop_list_new), ("dict()", loop_dict_new),
         ("ValueError(1)", loop_valueerror), ("ValueError()", loop_valueerror_noargs),
         ("Plain()", loop_plain_instance), ("int(7)", loop_int_from_int), ("bytes()", loop_bytes_new),
         ("range(2)", loop_range_new), ("cell(1)", loop_cell), ("lambda literal", loop_lambda)]
print("==", sys.version.split()[0])
for label, fn in CASES:
    fn()
    best = None
    for _ in range(REPS):
        t0 = time.perf_counter(); fn(); dt = time.perf_counter() - t0
        ns = dt * 1e9 / N
        best = ns if best is None or ns < best else best
    print(f"{label:18s} {best:9.1f} ns/iter")
