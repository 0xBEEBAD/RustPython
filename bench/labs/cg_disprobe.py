import dis, sys


def callee(a):
    return a


def loop(n):
    i = 0
    s = 0
    while i < n:
        s = callee(s) + i
        i += 1
    return s


print("=== interpreter:", sys.executable, sys.version.split()[0], "===")
print("--- module-level call target `callee` is a global name ---")
dis.dis(loop)
