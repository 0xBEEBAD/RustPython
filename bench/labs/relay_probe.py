# Probe the relay's exported data after a successful extension import.
import ctypes
import os
import sys

import _testsinglephase  # forces with_vm -> ensure_object_statics -> relay init

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.GetProcAddress.restype = ctypes.c_void_p
kernel32.GetProcAddress.argtypes = [ctypes.c_void_p, ctypes.c_char_p]

exe_dir = os.path.dirname(sys.executable)
relay = ctypes.WinDLL(os.path.join(exe_dir, "rustpythonapi.dll"))

def read16(handle, name):
    addr = kernel32.GetProcAddress(handle, name.encode())
    if not addr:
        return None
    return ctypes.string_at(addr, 128)

relay_data = read16(relay._handle, "PyUnicode_Type")
exe = ctypes.pythonapi
exe_data = read16(exe._handle, "PyUnicode_Type")

print("relay PyUnicode_Type words:", [int.from_bytes(relay_data[i*8:(i+1)*8], "little") for i in range(4)] if relay_data else None)
print("exe   PyUnicode_Type words:", [int.from_bytes(exe_data[i*8:(i+1)*8], "little") for i in range(4)] if exe_data else None)

# same for a PyExc slot
def readptr(handle, name):
    addr = kernel32.GetProcAddress(handle, name.encode())
    if not addr:
        return None
    return ctypes.cast(ctypes.c_void_p(addr), ctypes.POINTER(ctypes.c_void_p)).contents.value

print("relay PyExc_TypeError:", hex(readptr(relay._handle, "PyExc_TypeError") or 0))
print("exe   PyExc_TypeError:", hex(readptr(exe._handle, "PyExc_TypeError") or 0))
