import ctypes
class Flags(ctypes.Structure):
    _fields_ = [("a", ctypes.c_int, 1), ("b", ctypes.c_int, 3), ("c", ctypes.c_int, 4)]
f = Flags()
f.a = 1; f.b = 5; f.c = 9
r1 = (f.a, f.b, f.c)
# 正数测试
f2 = Flags(); f2.a = 1; f2.b = 3; f2.c = 7
r2 = (f2.a, f2.b, f2.c)
# 覆盖测试
f2.b = 2
r3 = (f2.a, f2.b, f2.c)
print("signed 9/5/1 ->", r1)
print("signed 7/3/1 ->", r2)
print("after b=2   ->", r3)
assert r2 == (1, 3, 7), r2
assert r3 == (1, 2, 7), r3
print("signed bitfields OK")
