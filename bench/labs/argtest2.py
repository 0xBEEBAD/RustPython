import codecs
import sys

sys.stdout.reconfigure(line_buffering=True)

d = codecs.lookup("utf-8").incrementaldecoder()
print("mro:", [c.__name__ for c in type(d).__mro__])
dec = type(d).__mro__[1].decode
print("resolved decode:", dec, "module:", dec.__module__)
print("is BufferedIncrementalDecoder.decode:", dec is codecs.BufferedIncrementalDecoder.decode)
print("is IncrementalDecoder.decode:", dec is codecs.IncrementalDecoder.decode)
import inspect

print("sig:", inspect.signature(dec))
# call the resolved function unbound with explicit self
r = dec(d, b"hello", True)
print("unbound resolved call:", r)
