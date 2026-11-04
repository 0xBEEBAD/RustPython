import codecs
import sys

sys.stdout.reconfigure(line_buffering=True)


def debug_buffer_decode(self, input, errors, final):
    print("  [_buffer_decode] input type:", type(input).__name__, "self:", type(self).__name__)
    return (input, len(input))


codecs.BufferedIncrementalDecoder._buffer_decode = debug_buffer_decode

d = codecs.lookup("utf-8").incrementaldecoder()
print("calling d.decode(b'hello', True)")
r = d.decode(b"hello", True)
print("result:", r)

# now restore and call the raw underlying
codecs.BufferedIncrementalDecoder._buffer_decode = codecs.utf_8_decode
print("restored, calling again")
try:
    r = d.decode(b"hello", True)
    print("result2:", r)
except TypeError as e:
    print("crash2:", e)
print("DONE")
