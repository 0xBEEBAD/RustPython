"""Parity test for PEP 810 lazy imports (source-level compatibility).

The test file itself must parse on CPython 3.14, which has no ``lazy``
statement syntax, so every lazy import lives in a string passed to exec() or
compile(). Genuine lazy-import cases run on CPython 3.15+ and on RustPython
builds that pre-process the keyword; on CPython 3.14 they are reported as
skipped. The non-lazy cases (strings, comments, identifiers) run everywhere
and verify that the pre-processor does not rewrite text that merely looks
like a lazy import.

Exit status is 0 only when every non-skipped check passes and prints
``RESULT OK``.
"""

import os
import sys
import traceback

PASS = []
FAIL = []
SKIP = []


def check(name, fn):
    try:
        fn()
    except Exception as exc:  # noqa: BLE001
        FAIL.append((name, exc))
        print(f"FAIL {name}: {type(exc).__name__}: {exc}")
        traceback.print_exc()
    else:
        PASS.append(name)
        print(f"PASS {name}")


def run(name, fn, needs_lazy=False):
    if needs_lazy and not HAS_LAZY:
        SKIP.append(name)
        print(f"SKIP {name} (lazy import syntax requires Python 3.15+)")
        return
    check(name, fn)


def _lazy_supported():
    try:
        compile("lazy import sys\n", "<lazy-probe>", "exec")
    except SyntaxError:
        return False
    return True


# CPython 3.14 reports 3.14 and rejects the syntax. RustPython also reports
# 3.14 but accepts it once the compiler pre-processor is present, so probe the
# parser instead of relying on sys.version_info alone.
HAS_LAZY = sys.version_info >= (3, 15) or _lazy_supported()


# --- lazy import cases (3.15+ / patched RustPython) ------------------------


def t_lazy_import():
    ns = {}
    exec("lazy import sys\n", ns)
    assert ns["sys"] is sys


def t_lazy_from_import():
    ns = {}
    exec("lazy from os import path\n", ns)
    assert ns["path"] is os.path


def t_lazy_import_alias():
    ns = {}
    exec("lazy import os as _os\n", ns)
    assert ns["_os"] is os


def t_lazy_inside_function():
    ns = {}
    exec(
        "def f():\n"
        "    lazy import sys\n"
        "    return sys\n",
        ns,
    )
    assert ns["f"]() is sys


def t_lazy_after_semicolon():
    ns = {}
    exec("x = 1; lazy import sys\n", ns)
    assert ns["x"] == 1
    assert ns["sys"] is sys


def t_lazy_compile_then_exec():
    src = "lazy import sys\nresult = sys.version_info[0]\n"
    code = compile(src, "<lazy-compile>", "exec")
    ns = {}
    exec(code, ns)
    assert ns["sys"] is sys
    assert ns["result"] == sys.version_info[0]


def t_lazy_line_numbers_preserved():
    src = (
        "# padding line\n"
        "value = 1\n"
        "lazy import sys\n"
        "raise RuntimeError('boom')\n"
    )
    try:
        exec(compile(src, "<lazy-lines>", "exec"), {})
    except RuntimeError:
        frames = traceback.extract_tb(sys.exc_info()[2])
        assert frames[-1].lineno == 4, f"expected line 4, got {frames[-1].lineno}"
    else:
        raise AssertionError("expected RuntimeError")


# --- non-lazy cases: these must never be rewritten -------------------------


def t_module_docstring_untouched():
    src = (
        '"""Module docstring.\n'
        "lazy import sys\n"
        "lazy from os import path\n"
        '"""\n'
    )
    ns = {}
    exec(src, ns)
    assert "lazy import sys" in ns["__doc__"]
    assert "lazy from os import path" in ns["__doc__"]


def t_function_docstring_untouched():
    src = (
        "def g():\n"
        "    '''Function docstring.\n"
        "lazy import sys\n"
        "    '''\n"
        "    return 2\n"
    )
    ns = {}
    exec(src, ns)
    assert ns["g"]() == 2
    assert "lazy import sys" in ns["g"].__doc__


def t_string_literals_untouched():
    src = (
        "a = 'lazy import sys'\n"
        'b = "lazy from os import path"\n'
        "c = '''\n"
        "lazy import sys\n"
        "'''\n"
        "d = r'''\n"
        "lazy from os import path\n"
        "'''\n"
    )
    ns = {}
    exec(src, ns)
    assert ns["a"] == "lazy import sys"
    assert ns["b"] == "lazy from os import path"
    assert ns["c"] == "\nlazy import sys\n"
    assert ns["d"] == "\nlazy from os import path\n"


def t_comment_untouched():
    ns = {}
    exec("# lazy import x\nvalue = 7\n", ns)
    assert ns["value"] == 7
    assert "x" not in ns


def t_variable_named_lazy():
    ns = {}
    exec("lazy = 5\nlazy_var = lazy + 1\n", ns)
    assert ns["lazy"] == 5
    assert ns["lazy_var"] == 6


run("lazy import sys", t_lazy_import, needs_lazy=True)
run("lazy from os import path", t_lazy_from_import, needs_lazy=True)
run("lazy import with alias", t_lazy_import_alias, needs_lazy=True)
run("lazy import inside a function", t_lazy_inside_function, needs_lazy=True)
run("lazy import after a semicolon", t_lazy_after_semicolon, needs_lazy=True)
run("exec(compile(lazy source))", t_lazy_compile_then_exec, needs_lazy=True)
run("line numbers preserved", t_lazy_line_numbers_preserved, needs_lazy=True)
run("module docstring untouched", t_module_docstring_untouched)
run("function docstring untouched", t_function_docstring_untouched)
run("string literals untouched", t_string_literals_untouched)
run("comment untouched", t_comment_untouched)
run("variable named lazy", t_variable_named_lazy)

print("=" * 40)
print(f"TOTAL {len(PASS) + len(FAIL)}  PASS {len(PASS)}  FAIL {len(FAIL)}  SKIP {len(SKIP)}")
for name, err in FAIL:
    print(f"  FAILED: {name}: {err}")
if FAIL:
    sys.exit(1)
print("RESULT OK")
