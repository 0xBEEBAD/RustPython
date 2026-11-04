# Call rustpythonapi_init manually and check whether the relay data fills in.
import ctypes
import os
import struct
import sys

import _testsinglephase  # forces with_vm -> ensure_object_statics

k = ctypes.WinDLL("kernel32")
k.GetProcAddress.restype = ctypes.c_void_p
k.GetProcAddress.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
k.GetModuleHandleW.restype = ctypes.c_void_p
k.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]

exe_dir = os.path.dirname(sys.executable)
r = ctypes.WinDLL(os.path.join(exe_dir, "rustpythonapi.dll"))

def relay_words(name):
    a = k.GetProcAddress(r._handle, name.encode())
    return [hex(x) for x in struct.unpack("<2Q", ctypes.string_at(a, 16))] if a else None

print("before manual init:", relay_words("PyUnicode_Type"))
init = k.GetProcAddress(r._handle, b"rustpythonapi_init")
print("init addr:", hex(init or 0))
f = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p)(init)
rc = f(k.GetModuleHandleW(None))
print("init rc:", rc)
print("after manual init: ", relay_words("PyUnicode_Type"))
