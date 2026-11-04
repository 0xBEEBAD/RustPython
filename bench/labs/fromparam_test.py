import ctypes
from ctypes import wintypes
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
@WNDENUMPROC
def enum_proc(hwnd, lparam):
    return True
print("enum_proc type:", type(enum_proc), type(enum_proc).__mro__)
r = WNDENUMPROC.from_param(enum_proc)
print("from_param:", r, type(r))
