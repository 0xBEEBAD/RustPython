class C1:
    def __dir__(self):
        return ["fox", "cow"]

for exe in [None]:
    pass
print("dir(C1) ->", dir(C1))
print("C1.__dir__ ->", C1.__dir__)
try:
    print("C1.__dir__() ->", C1.__dir__())
except TypeError as e:
    print("C1.__dir__() TypeError:", e)
print("type.__dir__(C1) ->", type.__dir__(C1))
import traceback
try:
    C1.foo
except AttributeError as exc:
    tb = exc.__traceback__
    print("helper ->", repr(traceback._compute_suggestion_error(exc, tb, exc.name)))
