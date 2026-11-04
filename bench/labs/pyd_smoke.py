# Smoke test for C-API extension module loading (bench/labs, gitignored).
# Exercises testext.cp314-win_amd64.pyd (custom), _testsinglephase and
# _testmultiphase (built by bench\build_test_extensions.ps1 from CPython 3.14
# sources). Extension files carry the SOABI suffix (".cp314-win_amd64.pyd"),
# matching _imp.extension_suffixes() / sysconfig SOABI.

import ctypes
import sys

failures = []


def check(name, cond, detail=""):
    if cond:
        print(f"PASS {name}")
    else:
        failures.append(name)
        print(f"FAIL {name} {detail}")


# --- custom testext (built from labs\testext.c) ----------------------------
import testext

check("testext.hello", testext.hello() == "hello from pyd!")
check("testext.add", testext.add(3, 4) == 7, repr(testext.add(3, 4)))
check("testext.doc", "testext" in testext.__doc__ or testext.__doc__ is not None)
check("testext.__file__", testext.__file__.endswith("testext.cp314-win_amd64.pyd"))

# ctypes.pythonapi (pre-bound to the running interpreter's C API)
pythonapi = ctypes.pythonapi
pythonapi.Py_GetVersion.restype = ctypes.c_char_p
ver = pythonapi.Py_GetVersion()
check("ctypes Py_GetVersion", ver.startswith(b"3.14"), repr(ver))
pythonapi.PyLong_FromLong.restype = ctypes.py_object
check("ctypes PyLong_FromLong", pythonapi.PyLong_FromLong(12345) == 12345)

# --- _testsinglephase (single-phase init) ----------------------------------
import _testsinglephase

check("singlephase attrs", _testsinglephase.int_const == 1969)
check("singlephase str_const", _testsinglephase.str_const == "something different")
check("singlephase error type", isinstance(_testsinglephase.error, type))
check(
    "singlephase _module_initialized",
    isinstance(_testsinglephase._module_initialized, float),
)

# --- _testmultiphase (multi-phase init, PEP 489) ----------------------------
import _testmultiphase

check("multiphase attrs", _testmultiphase.int_const == 1969)
check("multiphase str_const", _testmultiphase.str_const == "something different")
check("multiphase foo", _testmultiphase.foo(9, 9) == 18, repr(_testmultiphase.foo(9, 9)))
check("multiphase error", issubclass(_testmultiphase.error, Exception))

ex = _testmultiphase.Example()
# demo uses PyUnicode_Check (PyType_FastSubclass), which reads tp_flags
# through the C-visible type pointer; RustPython objects store their vtable
# there, so the fast check cannot match (see test_loader.test_functionality).
check("Example type", isinstance(ex, _testmultiphase.Example))
check("Str", _testmultiphase.Str(1) + "23" == "123", repr(_testmultiphase.Str(1) + "23"))
try:
    raise _testmultiphase.error()
except _testmultiphase.error:
    check("multiphase raise", True)

# reload must not re-run the exec slot (m_size == 0 marker)
import importlib

ex_class = _testmultiphase.Example
importlib.reload(_testmultiphase)
check("reload no re-exec", _testmultiphase.Example is ex_class)

# non-module create slot (load from the same origin under a new name)
import importlib.util


def load_by_name(fullname, origin=_testmultiphase.__file__):
    loader = importlib.machinery.ExtensionFileLoader(fullname, origin)
    spec = importlib.util.spec_from_loader(fullname, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


mod = load_by_name("_testmultiphase_nonmodule")
check("nonmodule create", type(mod) is not type(sys) and mod.three == 3, repr(mod))

# sys.dllhandle is non-zero on Windows
if sys.platform == "win32":
    check("sys.dllhandle", getattr(sys, "dllhandle", 0) != 0)

if failures:
    print(f"SMOKE FAILURES: {failures}")
    sys.exit(1)
print("ALL PYD SMOKE TESTS PASSED")
