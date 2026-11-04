import sys
import unittest

sys.stdout.reconfigure(line_buffering=True)

import importlib.util
import importlib.machinery
import _imp

# Replicate LoaderTests (Frozen) setUp + the 7 tests, then load the bad module.
from test.test_importlib import util

machinery = util.import_importlib("importlib.machinery")

EXTENSIONS = util.EXTENSIONS
LoaderClass = machinery["Frozen"].ExtensionFileLoader
loader = LoaderClass(EXTENSIONS.name, EXTENSIONS.file_path)
print("loader:", loader)

# test_module
with util.uncache(EXTENSIONS.name):
    module = loader.load_module(EXTENSIONS.name)
    print("module loaded:", module.__name__)

# test_module_reuse
with util.uncache(EXTENSIONS.name):
    m1 = loader.load_module(EXTENSIONS.name)
    m2 = loader.load_module(EXTENSIONS.name)
    print("reuse ok:", m1 is m2)

# test_load_module_API
with warnings  if False else __import__("warnings").catch_warnings():
    __import__("warnings").simplefilter("ignore", DeprecationWarning)
    loader.load_module()
    loader.load_module(None)
    try:
        loader.load_module("XXX")
        print("XXX: no error!")
    except ImportError as e:
        print("XXX ImportError:", e.name)

# now the bad module
f = importlib.machinery.ExtensionFileLoader(
    "_testmultiphase_exec_unreported_exception",
    r"C:\Dev2\luna-lang\RustPython\Lib\_testmultiphase.pyd",
)
spec = importlib.util.spec_from_loader("_testmultiphase_exec_unreported_exception", f)
m = _imp.create_dynamic(spec)
print("bad module created")
try:
    _imp.exec_dynamic(m)
    print("BAD: exec_dynamic returned without error")
except SystemError as e:
    print("GOOD: SystemError:", e)
    print("cause:", e.__cause__)
print("DONE")
