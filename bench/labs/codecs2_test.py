import codecs
import sys

sys.stdout.reconfigure(line_buffering=True)

print("utf_8_decode direct:")
r = codecs.utf_8_decode(b"hello", "strict", True)
print("direct:", r)

print("decode with explicit final=False:")
d = codecs.lookup("utf-8").incrementaldecoder()
r = d.decode(b"hello")
print("2-arg:", r)

print("_buffer_decode direct:")
r2 = codecs.BufferedIncrementalDecoder._buffer_decode(d, b"hello", "strict", True)
print("direct _buffer_decode:", r2)
