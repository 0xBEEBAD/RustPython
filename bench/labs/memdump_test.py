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


CFUNC = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)


@CFUNC
def demo(self, args):
    p.PyLong_FromLong.restype = ctypes.c_void_p
    p.PyLong_FromLong.argtypes = [ctypes.c_long]
    return p.PyLong_FromLong(args[0])


methods = (PyMethodDef * 2)(
    PyMethodDef(b"demo", ctypes.cast(demo, ctypes.c_void_p), 1, b"demo()"),
    PyMethodDef(None, None, 0, None),
)
print("methods addr:", hex(ctypes.addressof(methods)))
raw_name_ptr = ctypes.c_ulonglong.from_address(ctypes.addressof(methods)).value
print("raw ml_name ptr:", hex(raw_name_ptr))
print("string at raw ml_name ptr:", ctypes.string_at(raw_name_ptr))
print("raw method0 bytes:", ctypes.string_at(ctypes.addressof(methods), 32).hex())

# simulate what our Rust reads: slot array
doc = ctypes.create_string_buffer(b"Example doc")
slots = (PyTypeSlot * 3)(
    PyTypeSlot(56, ctypes.cast(doc, ctypes.c_void_p)),
    PyTypeSlot(64, ctypes.cast(methods, ctypes.c_void_p)),
    PyTypeSlot(0, None),
)
print("slots addr:", hex(ctypes.addressof(slots)))
print("raw slot bytes:", ctypes.string_at(ctypes.addressof(slots), 48).hex())
spec = PyTypeSpec(b"Example", 0, 0, 0, slots)
print("spec addr:", hex(ctypes.addressof(spec)))
print("DONE")
