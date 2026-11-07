"""Does RustPython build more traceback entries than CPython for the same raise?

bench.py's raise/catch row is 4.71x CPython and the recorded attribution says
two traceback entries cost ~320 ns of it, so the first question is whether the
two are even comparable objects. They are: measured 2026-11-07 on
rp-lite-119 and bench/labs/cp314, both report `entries per raise: [2, 2, 2]`
and the same `entry frames: ['<module>', 'throw']` for
`try: throw(i) except ValueError`. There is no extra entry to remove, which is
what makes the remaining gap purely per-entry cost.

    bench/labs/variants/rp-lite-119.exe bench/labs/tb_entry_count.py
    bench/labs/cp314/python.exe         bench/labs/tb_entry_count.py
"""


def depth(tb):
    n = 0
    while tb is not None:
        n += 1
        tb = tb.tb_next
    return n

def throw(i):
    raise ValueError(i)

counts = []
for _ in range(3):
    try:
        throw(1)
    except ValueError as e:
        counts.append(depth(e.__traceback__))
print("entries per raise:", counts)

# what does the handler see, and is the frame object materialized eagerly?
try:
    throw(7)
except ValueError as e:
    tb = e.__traceback__
    names = []
    while tb is not None:
        names.append(tb.tb_frame.f_code.co_name)
        tb = tb.tb_next
    print("entry frames:", names)
