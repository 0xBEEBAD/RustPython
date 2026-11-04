class Base:
    def decode(self, input, final=False):
        return input


class Sub(Base):
    pass


import codecs

print("argtest decode flags:", hex(Base.decode.__code__.co_flags))
print("codecs decode flags:", hex(codecs.BufferedIncrementalDecoder.decode.__code__.co_flags))
print("argtest argcount:", Base.decode.__code__.co_argcount)
print("codecs argcount:", codecs.BufferedIncrementalDecoder.decode.__code__.co_argcount)
