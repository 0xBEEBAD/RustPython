import ctypes
import sys

sys.stdout.reconfigure(line_buffering=True)
p = ctypes.pythonapi

s = "abcd"
print("string:", repr(s))

# Py_TYPE(s) via Py_REFCNT-style raw read? Use Py_TYPE export
p.Py_TYPE.restype = ctypes.c_void_p
p.Py_TYPE.argtypes = [ctypes.py_object]
type_ptr = p.Py_TYPE(s)
print("Py_TYPE(s):", hex(type_ptr))

Stub = ctypes.c_ulonglong * 16
stub = Stub.in_dll(p, "PyUnicode_Type")
unicode_addr = ctypes.addressof(stub)
print("PyUnicode_Type addr:", hex(unicode_addr))

p.PyType_IsSubtype.restype = ctypes.c_int
p.PyType_IsSubtype.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
r = p.PyType_IsSubtype(type_ptr, unicode_addr)
print("PyType_IsSubtype(Py_TYPE(s), PyUnicode_Type):", r)
print("DONE")
