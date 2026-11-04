import codecs
import sys

sys.stdout.reconfigure(line_buffering=True)


class Probe(codecs.BufferedIncrementalDecoder):
    def _buffer_decode(self, input, errors, final):
        print("inside _buffer_decode: input type:", type(input).__name__, "self:", self)
        return (input, len(input))


p = Probe()
print("p.buffer:", repr(p.buffer))
r = p.decode(b"hello", True)
print("result:", r)

# also probe the utf-8 one
d = codecs.lookup("utf-8").incrementaldecoder()
print("d.buffer:", repr(d.buffer))
try:
    r = d.decode(b"hello", True)
    print("utf8 result:", r)
except TypeError as e:
    print("utf8 crash:", e)
print("DONE")
