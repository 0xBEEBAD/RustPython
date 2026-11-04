import codecs
import sys

sys.stdout.reconfigure(line_buffering=True)

e = codecs.lookup("utf-8").incrementalencoder()
print("encoder:", e.encode("hello"))
print("encoder2:", e.encode("hello", True))

d = codecs.lookup("utf-8").incrementaldecoder()
print("decoder call via getattr method:")
try:
    print(d.decode(b"hi"))
except TypeError as ex:
    print("crash:", ex)

# bytes methods still fine?
print(b"abc".join([b"x"]))
print("'x'.join:", "x".join(["a", "b"]))
print("DONE")
