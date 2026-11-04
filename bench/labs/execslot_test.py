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

# get the def via PyModule_GetDef
p.PyModule_GetDef.restype = ctypes.c_void_p
p.PyModule_GetDef.argtypes = [ctypes.py_object]
defp = p.PyModule_GetDef(m)
print("def ptr:", hex(defp))

# read m_slots: CPyModuleDef layout: base(40) + name(8) + doc(8) + size(8) + methods(8) + slots(8)
slots_addr = ctypes.c_ulonglong.from_address(defp + 40 + 8 + 8 + 8 + 8).value
print("slots addr:", hex(slots_addr))
i = 0
while True:
    slot_id = ctypes.c_int.from_address(slots_addr + i * 16).value
    slot_val = ctypes.c_ulonglong.from_address(slots_addr + i * 16 + 8).value
    print(f"slot[{i}]: id={slot_id} value={hex(slot_val)}")
    if slot_id == 0:
        break
    i += 1

# find exec slot (id 2) and call it
for j in range(i + 1):
    slot_id = ctypes.c_int.from_address(slots_addr + j * 16).value
    slot_val = ctypes.c_ulonglong.from_address(slots_addr + j * 16 + 8).value
    if slot_id == 2:
        print("calling exec slot")
        EXEC = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p)
        p.Py_NewRef.restype = ctypes.c_void_p
        p.Py_NewRef.argtypes = [ctypes.py_object]
        modptr = p.Py_NewRef(m)
        rc = EXEC(slot_val)(modptr)
        print("exec rc:", rc)
        break
print("module attrs:", m.Example, m.error, m.Str, m.int_const, m.str_const)
print("DONE")
