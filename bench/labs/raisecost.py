"""Raise-path decomposition: ns per iteration for each stage between a plain
call and the bench.py shape (call + raise + catch across a frame boundary).

    python bench/labs/raisecost.py
"""
import timeit

N = 200_000


def throw(i):
    raise ValueError(i)


def catch(i):
    return i


def call_only(n):
    for i in range(n):
        catch(i)


def construct_only(n):
    for i in range(n):
        ValueError(i)


def raise_same_frame(n):
    for i in range(n):
        try:
            raise ValueError(i)
        except ValueError:
            pass


def raise_across_call(n):
    caught = 0
    for i in range(n):
        try:
            throw(i)
        except ValueError:
            caught += 1


def raise_no_arg_same_frame(n):
    for i in range(n):
        try:
            raise ValueError
        except ValueError:
            pass


def bare_except(n):
    for i in range(n):
        try:
            raise ValueError(i)
        except:
            pass


for name, fn in [
    ("call_only", call_only),
    ("construct_only", construct_only),
    ("raise_same_frame", raise_same_frame),
    ("raise_no_arg_same_frame", raise_no_arg_same_frame),
    ("bare_except", bare_except),
    ("across_call", raise_across_call),
]:
    best = min(timeit.repeat(lambda: fn(N), number=1, repeat=5))
    print(f"{name:32s} {best / N * 1e9:7.1f} ns/iter")
