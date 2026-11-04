import codecs
import sys

sys.stdout.reconfigure(line_buffering=True)

d = codecs.lookup("utf-8").incrementaldecoder()
cls = type(d)
print("class name:", cls.__name__, "module:", cls.__module__)
print("own dict:", {k: v for k, v in cls.__dict__.items() if not k.startswith("__")})

# subclass the frozen class in source
class P2(cls):
    pass


p2 = P2()
print("p2 class:", type(p2))
print("p2 decode func:", p2.decode.__func__)
try:
    r = p2.decode(b"hi", True)
    print("p2 decode ok:", r)
except TypeError as e:
    print("p2 crash:", e)

# compare: the frozen function called on the frozen d via PyBoundMethod vs on p2
print("d.decode func is p2.decode func:", d.decode.__func__ is p2.decode.__func__)
print("DONE")
