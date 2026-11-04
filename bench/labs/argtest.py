import sys

sys.stdout.reconfigure(line_buffering=True)


class C:
    def __init__(self):
        self.buffer = b""

    def decode(self, input, final=False):
        print("self ok, input type:", type(input).__name__, "final:", final)
        return self.buffer + input


c = C()
print("bound call")
print(c.decode(b"hello", True))
print("unbound call")
print(C.decode(c, b"hello", True))
print("2-arg method:")
print("xy".replace("x", "X"))
