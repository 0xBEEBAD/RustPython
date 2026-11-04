import sys

sys.stdout.reconfigure(line_buffering=True)

import importlib.util
import importlib.machinery
import _imp

names = [
    "_testmultiphase_bad_slot_large",
    "_testmultiphase_bad_slot_negative",
    "_testmultiphase_create_int_with_state",
    "_testmultiphase_create_null",
    "_testmultiphase_create_raise",
    "_testmultiphase_create_unreported_exception",
    "_testmultiphase_exec_err",
    "_testmultiphase_exec_raise",
    "_testmultiphase_exec_unreported_exception",
    "_testmultiphase_export_null",
    "_testmultiphase_export_raise",
    "_testmultiphase_export_uninitialized",
    "_testmultiphase_export_unreported_exception",
    "_testmultiphase_multiple_create_slots",
    "_testmultiphase_multiple_multiple_interpreters_slots",
    "_testmultiphase_negative_size",
]


def load_by_name(fullname):
    f = importlib.machinery.ExtensionFileLoader(
        fullname, r"C:\Dev2\luna-lang\RustPython\Lib\_testmultiphase.pyd"
    )
    spec = importlib.util.spec_from_loader(fullname, f)
    module = importlib.util.module_from_spec(spec)
    f.exec_module(module)
    return module


for name in names:
    try:
        load_by_name(name)
        print(f"{name}: NO ERROR")
    except SystemError as e:
        print(f"{name}: SystemError (cause={e.__cause__ is not None})")
    except BaseException as e:
        print(f"{name}: {type(e).__name__}: {e}")
print("DONE")
