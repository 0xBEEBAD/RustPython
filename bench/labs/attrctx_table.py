"""Truth table: when does CPython fill AttributeError.name / .obj?

Prints one row per attribute-mutation failure so the expectation for the Rust
side can be read off the reference interpreter instead of guessed.
"""

import sys


class Plain:
    pass


class Slotted:
    __slots__ = ("x",)


class WithProps:
    @property
    def ro(self):
        return 1


def row(label, fn):
    try:
        fn()
    except AttributeError as exc:
        obj = getattr(exc, "obj", "<no attr>")
        print(
            f"{label:34s} name={exc.name!r:18s} "
            f"obj={'set:' + type(obj).__name__ if obj != '<no attr>' else 'unset'} "
            f"msg={str(exc)[:46]!r}"
        )
    except Exception as exc:
        print(f"{label:34s} {type(exc).__name__}: {str(exc)[:40]}")
    else:
        print(f"{label:34s} no error")


print("interpreter:", sys.version.split()[0], sys.implementation.name)

p = Plain()
s = Slotted()
w = WithProps()

row("getattr instance missing", lambda: p.nope)
row("getattr class missing", lambda: Plain.nope)
row("getattr slotted missing", lambda: s.nope)
row("setattr slotted missing", lambda: setattr(s, "nope", 1))
row("setattr property read-only", lambda: setattr(w, "ro", 1))
row("delattr instance dict missing key", lambda: delattr(p, "nope"))
row("delattr slotted missing", lambda: delattr(s, "nope"))
row("delattr class missing", lambda: delattr(Plain, "nope"))
row("delattr property read-only", lambda: delattr(w, "ro"))
row("delattr no slots no dict", lambda: delattr(1, "nope"))
row("delattr after successful set", lambda: (setattr(p, "ok", 1), delattr(p, "ok")))
