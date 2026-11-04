import ctypes
from ctypes import wintypes

# 综合场景:GetSystemInfo(结构体指针)+ EnumWindows(回调)+ 结构体数组
class SYSTEM_INFO(ctypes.Structure):
    _fields_ = [
        ("wProcessorArchitecture", wintypes.WORD),
        ("wReserved", wintypes.WORD),
        ("dwPageSize", wintypes.DWORD),
        ("lpMinimumApplicationAddress", ctypes.c_void_p),
        ("lpMaximumApplicationAddress", ctypes.c_void_p),
        ("dwActiveProcessorMask", wintypes.DWORD),
        ("dwNumberOfProcessors", wintypes.DWORD),
        ("dwProcessorType", wintypes.DWORD),
        ("dwAllocationGranularity", wintypes.DWORD),
        ("wProcessorLevel", wintypes.WORD),
        ("wProcessorRevision", wintypes.WORD),
    ]

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
si = SYSTEM_INFO()
k32.GetSystemInfo(ctypes.byref(si))
print(f"page size: {si.dwPageSize}, procs: {si.dwNumberOfProcessors}, granularity: {si.dwAllocationGranularity}")

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
u32 = ctypes.WinDLL("user32", use_last_error=True)
u32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
u32.EnumWindows.restype = wintypes.BOOL
titles = []
@WNDENUMPROC
def cb(hwnd, lparam):
    buf = ctypes.create_unicode_buffer(256)
    n = u32.GetWindowTextW(hwnd, buf, 256)
    if n > 0:
        titles.append(buf.value)
    return True
u32.EnumWindows(cb, 0)
print(f"enumerated {len(titles)} titled windows, sample: {titles[:2]}")

# 结构体数组
class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
rects = (RECT * 2)()
rects[0].left = 10; rects[0].top = 20
rects[1].right = 30
print(f"rect[0]: {rects[0].left},{rects[0].top} rect[1].right: {rects[1].right}")
print("=== Win32 automation stack OK ===")
