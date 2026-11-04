"""Call _compute_suggestion_error directly: None, or an exception?"""

import sys
import traceback
import types

m = types.ModuleType("sugmod")
m.bluch = 1
m.__name__ = "sugmod"
sys.modules["sugmod"] = m

try:
    exec("from sugmod import blech")
except ImportError as exc:
    tb = exc.__traceback__
    print("wrong_name:", repr(exc.name_from), "module:", repr(exc.name))
    try:
        print("helper ->", repr(traceback._compute_suggestion_error(exc, tb, exc.name_from)))
    except Exception as inner:
        import traceback as tbmod

        tbmod.print_exc()
        print("helper raised:", type(inner).__name__, inner)
    print("format_exception tail:", traceback.format_exception(exc)[-1].rstrip()[-90:])

# AttributeError through a custom __dir__


class C:
    @classmethod
    def __dir__(cls):
        return ["fox"]


try:
    C.foo
except AttributeError as exc:
    tb = exc.__traceback__
    print("attr wrong_name:", repr(exc.name), "obj:", type(exc.obj).__name__)
    try:
        print("helper ->", repr(traceback._compute_suggestion_error(exc, tb, exc.name)))
    except Exception as inner:
        traceback.print_exc()
        print("helper raised:", type(inner).__name__, inner)
    print("format_exception tail:", traceback.format_exception(exc)[-1].rstrip()[-90:])

# and through a real module on disk, like the test does with make_module
import os
import tempfile

tmpdir = tempfile.mkdtemp()
sys.path.insert(0, tmpdir)
name = "diskmod"
with open(os.path.join(tmpdir, name + ".py"), "w") as fp:
    fp.write("bluch = 1\n")
try:
    exec(f"from {name} import blech")
except ImportError as exc:
    tb = exc.__traceback__
    print("disk .path:", repr(exc.path), ".name:", repr(exc.name))
    try:
        print("helper ->", repr(traceback._compute_suggestion_error(exc, tb, exc.name_from)))
    except Exception as inner:
        traceback.print_exc()
    print("tail:", traceback.format_exception(exc)[-1].rstrip()[-100:])
