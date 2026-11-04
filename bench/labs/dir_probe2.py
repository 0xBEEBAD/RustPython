import traceback


class M(type):
    def __dir__(cls):
        return [None, "fox"]


class C0:
    def __dir__(self):
        return [..., "bluch"]


class C1(C0, metaclass=M):
    pass


def inside(self, obj, name):
    return getattr(obj, name)


print("safe_dir(C1) ->", end=" ")
try:
    print(traceback._get_safe___dir__(C1))
except Exception as e:
    print("RAISED", type(e).__name__, e)

exc = None
try:
    inside("dummy-self", C1, "foo")
except AttributeError as e:
    exc = e
tb = exc.__traceback__
depth = 0
while tb.tb_next is not None:
    tb = tb.tb_next
    depth += 1
print("innermost frame:", tb.tb_frame.f_code.co_name, "depth", depth)
print("'self' in f_locals:", "self" in tb.tb_frame.f_locals)
print("f_locals keys:", sorted(tb.tb_frame.f_locals)[:6])
print("helper ->", repr(traceback._compute_suggestion_error(exc, exc.__traceback__, exc.name)))
