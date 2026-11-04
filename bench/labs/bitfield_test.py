import ctypes

class Flags(ctypes.Structure):
    _fields_ = [
        ("a", ctypes.c_int, 1),
        ("b", ctypes.c_int, 3),
        ("c", ctypes.c_int, 4),
    ]

f = Flags()
f.a = 1
f.b = 5
f.c = 9
print("a:", f.a, "b:", f.b, "c:", f.c)
assert f.a == 1 and f.b == 5 and f.c == 9, "bitfield readback failed"
# 覆盖测试
f.b = 2
assert f.a == 1 and f.b == 2 and f.c == 9, "bitfield overwrite failed"
print("overwrite ok:", f.a, f.b, f.c)
print("bitfields OK")
