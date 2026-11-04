import sys


def f(a):
    return a


class Holder:
    pass


print("f refcount:", sys.getrefcount(f))
print("f(1) refcount after:", sys.getrefcount(f))

# does a mortal object's refcount move during a call loop?
before = sys.getrefcount(f)
for _ in range(3):
    f(1)
after = sys.getrefcount(f)
print("delta across calls:", after - before)

# immortal-looking probe: clone-heavy loop, refcount must stay bounded
h = Holder()
print("h refcount:", sys.getrefcount(h))

# what does the globals dict hold for f?
g = globals()
print("g is globals():", g is globals())
print("'f' in g:", "f" in g)
