import traceback


class M(type):
    def __dir__(cls):
        return [None, "fox"]


class C0:
    def __dir__(self):
        return [..., "bluch"]


class C1(C0, metaclass=M):
    pass


class Holder:
    def attr_function(self, obj, name):
        return getattr(obj, name)

    def suggest(self, obj, name):
        try:
            self.attr_function(obj, name)
        except AttributeError as exc:
            lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
            return lines[-1].rstrip()
        return "<no error>"


h = Holder()
print("C1 foo ->", h.suggest(C1, "foo"))
print("C0     ->", h.suggest(C0, "blach"))
print("C0()   ->", h.suggest(C0(), "blach"))
print("C1()   ->", h.suggest(C1(), "foo"))
