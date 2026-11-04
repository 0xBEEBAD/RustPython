import ctypes
class Point(ctypes.Structure):
    _fields_ = [("x", ctypes.c_int), ("y", ctypes.c_int)]
pts = (Point * 3)()
pts[0].x = 7; pts[0].y = 8
pts[1].x = 9; pts[1].y = 10
print("pts[0]:", pts[0].x, pts[0].y)
print("pts[1]:", pts[1].x, pts[1].y)
print("pts[2]:", pts[2].x, pts[2].y)
assert (pts[0].x, pts[0].y) == (7, 8)
assert (pts[1].x, pts[1].y) == (9, 10)
# 通过元素写回
pts[2].x = 11
assert pts[2].x == 11
print("struct array elements OK")
