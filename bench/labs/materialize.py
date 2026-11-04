import sys, timeit
N = 300_000
get = sys._getframe


def plain(a):
    return a


def materialize(a, get=get):
    return get()


def materialize_twice(a, get=get):
    return get().f_lasti


for name, fn in [("plain", plain), ("_getframe (materializes)", materialize), ("_getframe+attr", materialize_twice)]:
    best = min(timeit.repeat(lambda: [fn(i) for i in range(N)], number=1, repeat=5))
    print(f"{name:30s} {best / N * 1e9:7.1f} ns/iter")
