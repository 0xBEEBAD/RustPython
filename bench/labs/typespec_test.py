import ctypes
import sys

sys.stdout.reconfigure(line_buffering=True)
p = ctypes.pythonapi


class PyTypeSlot(ctypes.Structure):
    _fields_ = [("slot", ctypes.c_int), ("pfunc", ctypes.c_void_p)]


class PyTypeSpec(ctypes.Structure):
    _fields_ = [
        ("name", ctypes.c_char_p),
        ("basicsize", ctypes.c_ssize_t),
        ("itemsize", ctypes.c_ssize_t),
        ("flags", ctypes.c_uint),
        ("slots", ctypes.POINTER(PyTypeSlot)),
    ]


class PyMethodDef(ctypes.Structure):
    _fields_ = [
        ("ml_name", ctypes.c_char_p),
        ("ml_meth", ctypes.c_void_p),
        ("ml_flags", ctypes.c_int),
        ("ml_doc", ctypes.c_char_p),
    ]


# A C function: (self, args) -> obj — returns a long from the first arg.
CFUNC_TYPE = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)


@CFUNC_TYPE
def demo(self, args):
    # args is a tuple; PyLong_FromLong(arg[0])
    p.PyLong_FromLong.restype = ctypes.py_object
    p.PyLong_FromLong.argtypes = [ctypes.c_long]
    return p.PyLong_FromLong(args[0])


p.PyType_FromSpec.restype = ctypes.py_object
p.PyType_FromSpec.argtypes = [ctypes.POINTER(PyTypeSpec)]

methods = (PyMethodDef * 2)(
    PyMethodDef(b"demo", ctypes.cast(demo, ctypes.c_void_p), 1, b"demo()"),  # METH_VARARGS
    PyMethodDef(None, None, 0, None),
)
# sanity: PyCFunction_NewEx reads the same raw memory
p.PyCFunction_NewEx.restype = ctypes.py_object
p.PyCFunction_NewEx.argtypes = [ctypes.POINTER(PyMethodDef), ctypes.c_void_p, ctypes.c_void_p]
f_sanity = p.PyCFunction_NewEx(ctypes.cast(methods, ctypes.POINTER(PyMethodDef)), None, None)
print("sanity PyCFunction name:", f_sanity.__name__)
doc = ctypes.create_string_buffer(b"Example doc")
slots = (PyTypeSlot * 3)(
    PyTypeSlot(56, ctypes.cast(doc, ctypes.c_void_p)),
    PyTypeSlot(64, ctypes.cast(methods, ctypes.c_void_p)),
    PyTypeSlot(0, None),
)
spec = PyTypeSpec(b"Example", 0, 0, 0, slots)
print("calling FromSpec")
t = p.PyType_FromSpec(ctypes.byref(spec))
print("type:", t)
print("type dict:", t.__dict__)
ex = t()
print("instance:", ex)
r = ex.demo(42)
print("demo(42):", r)
print("DONE")
