import sys, _imp
print("dllhandle:", sys.dllhandle)
import ctypes
print("pythonapi:", ctypes.pythonapi)
Py_GetVersion = ctypes.pythonapi.Py_GetVersion
Py_GetVersion.restype = ctypes.c_char_p
print("Py_GetVersion():", Py_GetVersion())
print("suffixes:", _imp.extension_suffixes())
import testext
print("testext:", testext, testext.hello(), testext.add(3, 4))
print("SMOKE2 OK")
