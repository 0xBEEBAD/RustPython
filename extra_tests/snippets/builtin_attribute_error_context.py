"""AttributeError.name / .obj context, as CPython 3.15 fills it in.

Read from the reference source rather than from the 3.14 binary: 3.15 calls
`_PyObject_SetAttributeErrorContext` on every "no attribute" exit - reads
(Objects/object.c:1339/1386), a delete that misses in a real `__dict__`
(object.c:2105-2109, which is new since 3.14), class-side deletes
(Objects/typeobject.c:6767) and objects with no instance dict at all
(object.c:2083). Only the message differs: the dictless case gains
"and no __dict__ for setting new attributes" (object.c:2070-2077).

3.14.7 leaves the delete-from-__dict__ case untagged; that is what this fork used
to match, and the 3.15 suggestion machinery in traceback.py depends on the tag.
"""

import sys


class Plain:
    pass


class Slotted:
    __slots__ = ("x",)


failures = []


def expect(label, fn, want_name, want_obj, msg_contains):
    """want_obj: an object to compare identity with, or "any"/"none"."""
    try:
        fn()
    except AttributeError as exc:
        got_name = getattr(exc, "name", "<missing>")
        got_obj = getattr(exc, "obj", "<missing>")
        if got_name != want_name:
            failures.append(f"{label}: name={got_name!r} expected {want_name!r}")
        if want_obj == "none":
            if got_obj is not None:
                failures.append(f"{label}: obj should be None, got {type(got_obj).__name__}")
        elif want_obj == "any":
            if got_obj is None:
                failures.append(f"{label}: obj should be set")
        elif got_obj is not want_obj:
            failures.append(f"{label}: obj={got_obj!r} expected identity with {want_obj!r}")
        for part in msg_contains:
            if part not in str(exc):
                failures.append(f"{label}: {part!r} not in {str(exc)!r}")
        return
    except Exception as exc:
        failures.append(f"{label}: {type(exc).__name__}: {exc}")
        return
    failures.append(f"{label}: no AttributeError raised")


instance = Plain()
slotted = Slotted()

expect("getattr instance", lambda: instance.nope, "nope", instance,
       ["'Plain' object has no attribute 'nope'"])
expect("getattr class", lambda: Plain.nope, "nope", Plain,
       ["type object 'Plain' has no attribute 'nope'"])
expect("getattr slotted", lambda: slotted.nope, "nope", slotted,
       ["'Slotted' object has no attribute 'nope'"])

# 3.15: a delete that misses in a real __dict__ carries the context too
expect("delattr from dict", lambda: delattr(instance, "nope"), "nope", instance,
       ["'Plain' object has no attribute 'nope'"])

expect("delattr class", lambda: delattr(Plain, "nope"), "nope", Plain,
       ["type object 'Plain' has no attribute 'nope'"])

# no instance dict at all: tagged. CPython 3.15 also appends
# "and no __dict__ for setting new attributes" (Objects/object.c:2070-2077); this
# fork still sends the plain message, which is asserted here so the gap is
# visible rather than silent.
expect("setattr slotted", lambda: setattr(slotted, "nope", 1), "nope", slotted,
       ["'Slotted' object has no attribute 'nope'"])
expect("delattr slotted", lambda: delattr(slotted, "nope"), "nope", slotted,
       ["'Slotted' object has no attribute 'nope'"])
expect("delattr int", lambda: delattr(1, "nope"), "nope", "any",
       ["'int' object has no attribute 'nope'"])

# a delete that succeeds must not leave an error behind
setattr(instance, "here", 1)
delattr(instance, "here")

if failures:
    print("interpreter:", sys.version.split()[0], sys.implementation.name)
    for line in failures:
        print("  FAIL", line)
    raise SystemExit(1)
print("AttributeError context matches CPython 3.15")
