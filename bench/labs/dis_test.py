import codecs
import dis
import sys

sys.stdout.reconfigure(line_buffering=True)

f = codecs.BufferedIncrementalDecoder.decode
print("== frozen decode dis ==")
dis.dis(f)

print("== source decode dis ==")
exec("class B:\n    def decode(self, input, final=False):\n        data = self.buffer + input\n        return data")
dis.dis(B.decode)
print("DONE")
