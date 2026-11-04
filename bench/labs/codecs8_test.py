import codecs
import sys

sys.stdout.reconfigure(line_buffering=True)

d = codecs.lookup("utf-8").incrementaldecoder()
f = codecs.BufferedIncrementalDecoder.decode
print("keyword call:")
try:
    r = f(d, input=b"hello", final=True)
    print("ok:", r)
except TypeError as e:
    print("crash:", e)

print("positional with 2 args:")
try:
    r = f(d, b"hello")
    print("ok:", r)
except TypeError as e:
    print("crash:", e)

print("positional with 3 args:")
try:
    r = f(d, b"hello", True)
    print("ok:", r)
except TypeError as e:
    print("crash:", e)
print("DONE")
