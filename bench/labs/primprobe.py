"""Primitive-cost probe: isolates single VM operations from the loop floor.

Pairs are chosen so the difference between adjacent cases attributes cost to
one operation (refcount pair, tracked alloc, builtin call, arith, ...).
"""
import sys
import time

REPS = 7
N = 1_000_000

g_list = [1, 2, 3]
g_int = 7
g_float = 1.5
g_str = "abc"
g_type = ValueError


def b_loop(n):
    for _ in range(n):
        pass


def b_true(n):
    for _ in range(n):
        x = True


def b_imm_int(n):
    for _ in range(n):
        x = g_int


def b_list_ref(n):
    for _ in range(n):
        x = g_list


def b_type_ref(n):
    for _ in range(n):
        x = g_type


def b_list_new(n):
    for _ in range(n):
        x = []


def b_list_1(n):
    for _ in range(n):
        x = [g_list]


def b_dict_new(n):
    for _ in range(n):
        x = {}


def b_set_new(n):
    for _ in range(n):
        x = set()


def b_object_new(n):
    for _ in range(n):
        x = object()


def b_int_add(n):
    for _ in range(n):
        x = 1 + 2


def b_float_add(n):
    for _ in range(n):
        x = 1.0 + 2.0


def b_str_concat(n):
    for _ in range(n):
        x = "a" + "b"


def b_len_builtin(n):
    for _ in range(n):
        x = len(g_list)


def b_list_copy(n):
    for _ in range(n):
        x = g_list.copy()


def b_tuple_new(n):
    for _ in range(n):
        x = (g_list,)


CASES = [
    ("loop only", b_loop),
    ("store True (immortal)", b_true),
    ("load global int", b_imm_int),
    ("load global list", b_list_ref),
    ("load global type", b_type_ref),
    ("list []", b_list_new),
    ("list [x]", b_list_1),
    ("dict {}", b_dict_new),
    ("set()", b_set_new),
    ("object()", b_object_new),
    ("tuple (x,)", b_tuple_new),
    ("1+2", b_int_add),
    ("1.0+2.0", b_float_add),
    ("'a'+'b'", b_str_concat),
    ("len(list)", b_len_builtin),
    ("list.copy()", b_list_copy),
]


def main():
    print(f"=== {sys.implementation.name} python {sys.version.split()[0]} ===")
    vals = {}
    for name, fn in CASES:
        best = float("inf")
        for _ in range(REPS):
            t0 = time.perf_counter()
            fn(N)
            dt = time.perf_counter() - t0
            if dt < best:
                best = dt
        vals[name] = best / N * 1e9
    base = vals["loop only"]
    for name, _ in CASES:
        print(f"{name:22s} {vals[name]:9.1f} ns   net {vals[name] - base:8.1f}")


if __name__ == "__main__":
    main()
