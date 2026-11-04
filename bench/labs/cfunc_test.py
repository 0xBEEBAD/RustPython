import ctypes
import sys

sys.stdout.reconfigure(line_buffering=True)
p = ctypes.pythonapi


class PyMethodDef(ctypes.Structure):
    _fields_ = [
        ("ml_name", ctypes.c_char_p),
        ("ml_meth", ctypes.c_void_p),
        ("ml_flags", ctypes.c_int),
        ("ml_doc", ctypes.c_char_p),
    ]


CFUNC = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)


@CFUNC
def hello(self, args):
    p.PyLong_FromLong.restype = ctypes.c_void_p
    p.PyLong_FromLong.argtypes = [ctypes.c_long]
    return p.PyLong_FromLong(42)


m = PyMethodDef(b"demo", ctypes.cast(hello, ctypes.c_void_p), 1, b"doc")
p.PyCFunction_NewEx.restype = ctypes.py_object
p.PyCFunction_NewEx.argtypes = [ctypes.POINTER(PyMethodDef), ctypes.c_void_p, ctypes.c_void_p]
f = p.PyCFunction_NewEx(ctypes.byref(m), None, None)
print("fn:", f, f.__name__)

d = {"demo": f}
B = type("B", (object,), d)
print("B dict:", B.__dict__)
b = B()
print("call via instance:", b.demo())
print("DONE")
