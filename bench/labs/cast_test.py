import ctypes
from ctypes import wintypes

# 1. cast(byref(x))
class Point(ctypes.Structure):
    _fields_ = [("x", ctypes.c_int), ("y", ctypes.c_int)]
p = Point(1, 2)
addr = ctypes.cast(ctypes.byref(p), ctypes.c_void_p)
print("cast(byref):", hex(addr.value))
assert addr.value == ctypes.addressof(p)
print("cast byref OK")

# 2. cast 回调
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
@WNDENUMPROC
def cb(h, l):
    return True
fptr = ctypes.cast(cb, ctypes.c_void_p)
print("cast(callback):", hex(fptr.value))
assert fptr.value != 0
print("cast callback OK")
