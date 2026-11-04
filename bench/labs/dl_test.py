import ctypes
try:
    d = ctypes.CDLL(r"C:\Dev2\luna-lang\RustPython\target\release\python311.dll")
    print("loaded python311.dll, handle:", hex(d._handle))
    d.Py_GetVersion.restype = ctypes.c_char_p
    print("Py_GetVersion:", d.Py_GetVersion())
except Exception as e:
    print("FAIL:", type(e).__name__, e)
try:
    t = ctypes.CDLL(r"C:\Dev2\luna-lang\RustPython\bench\labs\testext.pyd")
    print("loaded testext.pyd, handle:", hex(t._handle))
    t.PyInit_testext.restype = ctypes.c_void_p
    print("PyInit_testext:", t.PyInit_testext())
except Exception as e:
    print("FAIL2:", type(e).__name__, e)
