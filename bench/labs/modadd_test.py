import ctypes
import sys

sys.stdout.reconfigure(line_buffering=True)
p = ctypes.pythonapi

import importlib.util, importlib.machinery, _imp

f = importlib.machinery.ExtensionFileLoader(
    "_testmultiphase", r"C:\Dev2\luna-lang\RustPython\Lib\_testmultiphase.pyd"
)
spec = importlib.util.spec_from_loader("_testmultiphase", f)
m = _imp.create_dynamic(spec)
print("created", m)

p.PyErr_NewException.restype = ctypes.py_object
p.PyErr_NewException.argtypes = [ctypes.c_char_p, ctypes.c_void_p, ctypes.c_void_p]
e = p.PyErr_NewException(b"_testimportexec.error", None, None)
print("exc:", e, issubclass(e, Exception))

p.PyModule_AddObjectRef.restype = ctypes.c_int
p.PyModule_AddObjectRef.argtypes = [ctypes.py_object, ctypes.c_char_p, ctypes.py_object]
r = p.PyModule_AddObjectRef(m, b"error", e)
print("add objref:", r, getattr(m, "error", None) is e)

p.PyModule_AddIntConstant.restype = ctypes.c_int
p.PyModule_AddIntConstant.argtypes = [ctypes.py_object, ctypes.c_char_p, ctypes.c_long]
r = p.PyModule_AddIntConstant(m, b"int_const", 1969)
print("add int:", r, m.int_const)

p.PyModule_AddStringConstant.restype = ctypes.c_int
p.PyModule_AddStringConstant.argtypes = [ctypes.py_object, ctypes.c_char_p, ctypes.c_char_p]
r = p.PyModule_AddStringConstant(m, b"str_const", b"something different")
print("add str:", r, m.str_const)

p.PyModule_Add.restype = ctypes.c_int
p.PyModule_Add.argtypes = [ctypes.py_object, ctypes.c_char_p, ctypes.py_object]
r = p.PyModule_Add(m, b"err2", e)
print("add:", r, getattr(m, "err2", None) is e)
print("DONE")
