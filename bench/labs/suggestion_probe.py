"""Do the exception attributes the 3.15 suggestion code reads actually exist?

Lib/traceback.py branches on ImportError.name_from, AttributeError.name/.obj and
NameError.name. If our raise sites leave those unset the suggestion never forms,
which is what the four test_traceback failures look like.
"""

import sys

print("interpreter:", sys.version.split()[0], sys.implementation.name)

try:
    "".foo
except AttributeError as exc:
    print("AttributeError .name:", repr(getattr(exc, "name", "<MISSING SLOT>")))
    print("AttributeError .obj type:", type(getattr(exc, "obj", "<MISSING SLOT>")).__name__)

try:
    None.foo
except AttributeError as exc:
    print("None.foo .name:", repr(getattr(exc, "name", "<MISSING SLOT>")))


class C:
    @classmethod
    def __dir__(cls):
        return ["fox"]


try:
    C.foo
except AttributeError as exc:
    print("custom __dir__ .name:", repr(getattr(exc, "name", "<MISSING SLOT>")))
    print("custom __dir__ .obj is C:", getattr(exc, "obj", None) is C)

m = __import__("types").ModuleType("sugmod")
m.bluch = 1
sys.modules["sugmod"] = m
try:
    exec("from sugmod import blech")
except ImportError as exc:
    print("ImportError type:", type(exc).__name__)
    print("ImportError .name:", repr(getattr(exc, "name", "<MISSING SLOT>")))
    print("ImportError .path:", repr(getattr(exc, "path", "<MISSING SLOT>")))
    print("ImportError .name_from:", repr(getattr(exc, "name_from", "<MISSING SLOT>")))

try:
    import sugmod.bluch.deep  # noqa: F401
except (ModuleNotFoundError, ImportError) as exc:
    print("ModuleNotFoundError .name:", repr(getattr(exc, "name", "<MISSING SLOT>")))

try:
    eval("undefinednamexyz")  # noqa
except NameError as exc:
    print("NameError .name:", repr(getattr(exc, "name", "<MISSING SLOT>")))

import traceback

print("stdlib_module_names present:", hasattr(sys, "stdlib_module_names"))
print("flags.no_site:", sys.flags.no_site)
