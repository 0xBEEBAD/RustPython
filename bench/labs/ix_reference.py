"""What our `ArgIndex`/`ArgSize` binder already gets right, measured.

Task #110 is that `str.split(sep, Idx())` and friends reject an object with
`__index__` because their fields are typed `isize` / `Option<PyIntRef>` instead.
The proposed fix is to switch those fields to the binder that `range`,
`slice.indices` and the method descriptor already use, so before making the
change it is worth knowing what that binder actually does at the Python level -
otherwise the swap could silently change error text or swallow exceptions.

    bench/labs/variants/rp-lite-119.exe bench/labs/ix_reference.py
    bench/labs/cp314/python.exe         bench/labs/ix_reference.py

Measured on 2026-11-07, the two interpreters agree on every row here:
`Idx` is accepted (range gives [0,1,2,3], indices gives (0,4,1)); a `__index__`
that returns a float raises TypeError; a `__index__` that raises propagates the
RuntimeError rather than turning it into TypeError; a plain `str` gives exactly
CPython's "'str' object cannot be interpreted as an integer"; and 2**70 is
clamped, not overflowed, in `indices`. So switching str/bytes integer arguments
to this binder buys `__index__` support, CPython-shaped messages and correct
exception propagation in one move.

Two rows still differ in wording only. Ours says
`BadFloat.__index__ returned non-int(type float)` where the 3.14.7 binary says
`__index__ returned non-int (type float)` - and neither is the target: CPython
3.15 raises `"%T.__index__() must return an int, not %T"`
(Object/abstract.c:1434, with a second form at :1441 for the strict-subclass
DeprecationWarning), so the 3.14.7 binary is not the authority for this row and
the 3.15 text is what to match. Separately, the `isize` overflow text is
"Python int too large to convert to Rust isize" against CPython's "C ssize_t",
and that string lives in a shared site (builtins/int.rs:365-375) which this
change must not edit.
"""


class Idx:
    def __index__(self):
        return 4


class BadFloat:
    def __index__(self):
        return 1.5


class RaiseIdx:
    def __index__(self):
        raise RuntimeError("boom")


def show(label, fn):
    try:
        print("%-26s %r" % (label, fn()))
    except BaseException as e:
        print("%-26s RAISED %s: %s" % (label, type(e).__name__, e))


show("range(Idx)", lambda: list(range(Idx())))
show("slice.indices(Idx)", lambda: slice(None).indices(Idx()))
show("slice.indices(BadFloat)", lambda: slice(None).indices(BadFloat()))
show("slice.indices(RaiseIdx)", lambda: slice(None).indices(RaiseIdx()))
show("slice.indices('x')", lambda: slice(None).indices("x"))
show("2**70 to indices", lambda: slice(None).indices(2**70))
