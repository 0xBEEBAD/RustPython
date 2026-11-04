import ctypes
class U(ctypes.Structure):
    _fields_ = [("a", ctypes.c_uint, 1), ("b", ctypes.c_uint, 3), ("c", ctypes.c_uint, 4)]
u = U(); u.a = 1; u.b = 5; u.c = 9
print("unsigned:", u.a, u.b, u.c)
assert (u.a, u.b, u.c) == (1, 5, 9)
print("unsigned OK")
