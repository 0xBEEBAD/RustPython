import codecs
import sys

sys.stdout.reconfigure(line_buffering=True)

cls = codecs.lookup("utf-8").incrementaldecoder.__class__
print("class:", cls)
print("dict keys:", list(cls.__dict__.keys()))
print("base:", cls.__bases__)
dec = cls.__dict__.get("decode")
print("own decode:", dec)
d = codecs.lookup("utf-8").incrementaldecoder()
print("bound func module:", d.decode.__func__.__module__)
print("bound func code name:", d.decode.__func__.__code__.co_name)
# what does the bound method's call see? try calling via the base class function explicitly
f = codecs.BufferedIncrementalDecoder.decode
print("unbound call with explicit self:")
try:
    r = f(d, b"hello", True)
    print("ok:", r)
except TypeError as e:
    print("crash:", e)
print("DONE")
