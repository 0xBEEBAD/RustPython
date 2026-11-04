import ctypes
from ctypes import wintypes

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL

count = [0]
titles = []
@WNDENUMPROC
def enum_proc(hwnd, lparam):
    count[0] += 1
    return True

ok = user32.EnumWindows(enum_proc, 0)
print("EnumWindows ok:", bool(ok), "windows:", count[0])
assert ok and count[0] > 0
print("callback as argument OK")
