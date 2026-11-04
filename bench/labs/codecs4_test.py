import codecs
import sys

sys.stdout.reconfigure(line_buffering=True)

d = codecs.BufferedIncrementalDecoder.__dict__["decode"]
print("class dict decode:", d, type(d))
print("argtest comparison:")
exec("class B:\n    def decode(self, input, final=False):\n        return input")
bd = B.__dict__["decode"]
print("plain class dict decode:", bd, type(bd))
print("DONE")
