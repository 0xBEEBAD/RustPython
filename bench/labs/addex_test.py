import ctypes
import sys

sys.stdout.reconfigure(line_buffering=True)
p = ctypes.pythonapi
p.PyErr_NewException.restype = ctypes.py_object
p.PyErr_NewException.argtypes = [ctypes.c_char_p, ctypes.py_object, ctypes.py_object]
exc = p.PyErr_NewException(b"_testimportexec.error", None, None)
print("exception:", exc, issubclass(exc, Exception))

# module add functions
p.PyModule_AddObjectRef.restype = ctypes.c_int
p.PyModule_AddObjectRef.argtypes = [ctypes.py_object, ctypes.c_char_p, ctypes.py_object]
p.PyModule_AddIntConstant.restype = ctypes.c_int
p.PyModule_AddIntConstant.argtypes = [ctypes.py_object, ctypes.c_char_p, ctypes.c_long]
p.PyModule_AddStringConstant.restype = ctypes.c_int
p.PyModule_AddStringConstant.argtypes = [ctypes.py_object, ctypes.c_char_p, ctypes.c_char_p]

import types as _types

ns = _types.SimpleNamespace()
r = p.PyModule_AddObjectRef(ns, b"error", exc)
print("add objectref:", r, getattr(ns, "error", None) is exc)
r = p.PyModule_AddIntConstant(ns, b"int_const", 1969)
print("add int:", r, ns.int_const)
r = p.PyModule_AddStringConstant(ns, b"str_const", b"something different")
print("add str:", r, ns.str_const)
print("DONE")
