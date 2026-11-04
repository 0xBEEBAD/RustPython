import importlib.util
import sys

sys.stdout.reconfigure(line_buffering=True)

# Load codecs from source under a fresh name
spec = importlib.util.spec_from_file_location("codecs_src", r"Lib\codecs.py")
csrc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(csrc)
print("loaded source codecs")

d = csrc.lookup("utf-8").incrementaldecoder()
f = csrc.BufferedIncrementalDecoder.decode
print("flags:", hex(f.__code__.co_flags))
print("unbound:", f(d, b"hello", True))
print("bound:", d.decode(b"world", True))

# and the frozen one
import codecs

df = codecs.lookup("utf-8").incrementaldecoder()
ff = codecs.BufferedIncrementalDecoder.decode
print("frozen flags:", hex(ff.__code__.co_flags))
print("frozen unbound:", ff(df, b"hello", True))
