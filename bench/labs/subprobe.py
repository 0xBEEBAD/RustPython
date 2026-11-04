"""Subscript probe: exact list/tuple/dict lookups and str slices."""
import sys
import time

lst = [10, 20, 30]
tup = (10, 20, 30)
dct = {"k": 1, "j": 2}
s = "abcdefghij" * 10
N = 300000


def b_loop(n):
    for _ in range(n):
        pass


def b_list(n):
    for _ in range(n):
        x = lst[1]


def b_list_neg(n):
    for _ in range(n):
        x = lst[-1]


def b_tuple(n):
    for _ in range(n):
        x = tup[0]


def b_dict(n):
    for _ in range(n):
        x = dct["k"]


def b_len_list(n):
    for _ in range(n):
        x = len(lst)


def b_len_str(n):
    for _ in range(n):
        x = len(s)


def b_str_slice(n):
    for _ in range(n):
        x = s[3:7]


CASES = [
    ("loop only", b_loop),
    ("list[1]", b_list),
    ("list[-1]", b_list_neg),
    ("tuple[0]", b_tuple),
    ("dict['k']", b_dict),
    ("len(list)", b_len_list),
    ("len(str)", b_len_str),
    ("str[3:7]", b_str_slice),
]


def main():
    print(f"=== {sys.implementation.name} ===")
    for name, fn in CASES:
        best = float("inf")
        for _ in range(5):
            t0 = time.perf_counter()
            fn(N)
            dt = time.perf_counter() - t0
            best = min(best, dt)
        print(f"{name:16s} {best / N * 1e9:9.1f} ns")


if __name__ == "__main__":
    main()
