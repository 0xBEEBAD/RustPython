import codecs
import sys

sys.stdout.reconfigure(line_buffering=True)

d = codecs.lookup("utf-8").incrementaldecoder()
dec = d.decode
print("type of d.decode:", type(dec))
print("is bound method:", type(dec).__name__)
print("func:", getattr(dec, "__func__", None))
print("self:", getattr(dec, "__self__", None))
print("call via dec:", dec(b"hello", True))
