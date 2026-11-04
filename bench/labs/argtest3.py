import sys

sys.stdout.reconfigure(line_buffering=True)


class Base:
    def __init__(self):
        self.buffer = b""

    def decode(self, input, final=False):
        print("  input type:", type(input).__name__, "final:", final)
        return self.buffer + input


class Sub(Base):
    pass


s = Sub()
print("inherited bound call:")
print(s.decode(b"hello", True))
print("inherited unbound call:")
print(Base.decode(s, b"hello", True))
print("DONE")
