"""Observable-behaviour digest for the exception args plumbing.

Prints one line per behaviour that the args-tuple change could plausibly
disturb: `e.args` contents and identity, `__new__`/`__init__` override
combinations, keyword handling, `__reduce__`, pickling, copy, and the
specialised exception inits (OSError / ImportError / SyntaxError /
UnicodeDecodeError).

Run under both interpreters and diff:
    <rustpython> bench/labs/args_sem.py > temp/sem-base.txt
    cp314        bench/labs/args_sem.py > temp/sem-cp.txt
Identity lines (`is`) are the discriminator for a shared/reused args tuple.

"""

import copy
import pickle
import sys


def show(label, fn):
    try:
        print(f"{label}: {fn()!r}")
    except BaseException as e:
        print(f"{label}: EXC {type(e).__name__}: {e}")


class Plain(Exception):
    pass


class OnlyNew(Exception):
    created = []

    def __new__(cls, *a, **kw):
        self = Exception.__new__(cls, *a, **kw)
        OnlyNew.created.append(("new", a, tuple(sorted(kw))))
        return self


class OnlyInit(Exception):
    inited = []

    def __init__(self, *a, **kw):
        OnlyInit.inited.append(("init", a, tuple(sorted(kw))))


class BothNewInit(Exception):
    log = []

    def __new__(cls, *a, **kw):
        BothNewInit.log.append(("new", a))
        return super().__new__(cls, *a)

    def __init__(self, *a, **kw):
        BothNewInit.log.append(("init", a))
        super().__init__(*a)


class NewReturnsOther(Exception):
    calls = []

    def __new__(cls, *a, **kw):
        return Plain("substitute")

    def __init__(self, *a, **kw):
        NewReturnsOther.calls.append(("init", a))


class ArgsReassign(Exception):
    def __new__(cls, *a, **kw):
        self = Exception.__new__(cls)
        self.args = ("hard-coded",)
        return self


def cases():
    show("args-one", lambda: ValueError("x").args)
    show("args-none", lambda: ValueError().args)
    show("args-two", lambda: ValueError("x", "y").args)
    show("args-str", lambda: str(ValueError("x")))
    show("args-str-multi", lambda: str(ValueError("x", "y")))
    show("args-repr", lambda: repr(ValueError("x")))
    show("args-is-stable", lambda: (lambda e: (lambda t: e.args is t)(e.args))(ValueError("x")))
    show("init-again-identity", lambda: (lambda e: (lambda t: (e.__init__("x"), e.args is t, e.args)[1:])(e.args))(ValueError("x")))
    show("init-again-content", lambda: (lambda e: (e.__init__("y"), e.args)[1])(ValueError("x")))
    show("init-empty-then-args", lambda: (lambda e: (e.__init__("a", "b"), e.args)[1])(ValueError()))
    show("init-noargs-clears", lambda: (lambda e: (e.__init__(), e.args)[1])(ValueError("x")))
    show("new-only", lambda: ValueError.__new__(ValueError, "x").args)
    show("new-then-init", lambda: (lambda e: (e.__init__("y"), e.args)[1])(ValueError.__new__(ValueError, "x")))
    show("args-getset-type", lambda: type(ValueError("x").args))
    show("args-setter-tuple", lambda: (lambda e: (setattr(e, "args", ("z",)), e.args)[1])(ValueError("x")))
    show("args-setter-list", lambda: (lambda e: (setattr(e, "args", ["z"]), e.args)[1])(ValueError("x")))
    show("args-setter-str", lambda: (lambda e: (setattr(e, "args", "zy"), e.args)[1])(ValueError("x")))
    show("args-setter-int", lambda: (lambda e: (setattr(e, "args", 3), None)[1])(ValueError("x")))
    show("args-deleter", lambda: (lambda e: (delattr(e, "args"), None)[1])(ValueError("x")))
    show("base-kwargs", lambda: BaseException(k=1))
    show("plain-kwargs", lambda: Plain(k=1).args)
    show("reduce-args", lambda: ValueError("x").__reduce__())
    show("reduce-dict", lambda: (lambda e: (setattr(e, "note", 1), e.__reduce__())[1])(ValueError("x")))
    show("pickle-roundtrip", lambda: pickle.loads(pickle.dumps(ValueError("x"))).args)
    show("pickle-roundtrip-msg", lambda: str(pickle.loads(pickle.dumps(ValueError("x")))))
    show("pickle-subclass", lambda: pickle.loads(pickle.dumps(Plain("x"))).args)
    show("copy-subclass", lambda: copy.copy(Plain("x")).args)
    show("deepcopy-subclass", lambda: copy.deepcopy(Plain("x")).args)
    show("copy-exc-with-dict", lambda: (lambda e: (setattr(e, "note", 1), copy.copy(e).__dict__)[1])(ValueError("x")))
    show("type-of-instance-call", lambda: type(ValueError("x"))("q").args)
    show("raise-exc-info-args", lambda: (lambda: (lambda: (_ for _ in ()).throw(ValueError("boom")))())() if False else None)
    show("override-new-log", lambda: (OnlyNew.created.clear(), OnlyNew("a"), OnlyNew.created[:], OnlyNew("a").args)[2:])
    show("override-init-log", lambda: (OnlyInit.inited.clear(), OnlyInit("a"), OnlyInit.inited[:], OnlyInit("a").args)[2:])
    show("override-both-log", lambda: (BothNewInit.log.clear(), BothNewInit("a"), BothNewInit.log[:], BothNewInit("a").args)[2:])
    show("new-returns-other", lambda: (NewReturnsOther.calls.clear(), r := NewReturnsOther("a"), (type(r).__name__, r.args, NewReturnsOther.calls[:])[1:])[2])
    show("new-sets-args-then-init", lambda: ArgsReassign("ignored").args)
    show("subclass-of-valueerror", lambda: (lambda C: C("x").args)(type("E", (ValueError,), {})))
    show("subclass-override-init", lambda: (lambda C: C("x").args)(type("E", (ValueError,), {"__init__": lambda self: None})))
    show("oserror-args", lambda: OSError(2, "msg").args)
    show("oserror-str", lambda: str(OSError(2, "msg")))
    show("oserror-reduce", lambda: (lambda e: (e.filename, e.errno, e.strerror, e.args))(OSError(2, "msg", "f")))
    show("importerror-args", lambda: ImportError("m").args)
    show("importerror-name", lambda: (lambda e: (e.name, e.path, e.args))(ImportError("m", name="n", path="p")))
    show("syntaxerror-args", lambda: SyntaxError("f").args)
    show("syntaxerror-full", lambda: (lambda e: (e.msg, e.lineno, e.args))(SyntaxError("m", ("f", 1, 2, "t"))))
    show("unicodedecode-args", lambda: UnicodeDecodeError("utf8", b"", 0, 1, "r").args)
    show("unicodedecode-reduce", lambda: UnicodeDecodeError("utf8", b"", 0, 1, "r").__reduce__())
    show("stopiteration-args", lambda: StopIteration("v").args)
    show("stopiteration-value", lambda: StopIteration("v").value)
    show("attributeerror-args", lambda: AttributeError("a").args)
    show("nameerror-args", lambda: NameError("n").args)
    show("systemexit-args", lambda: SystemExit(3).args)
    show("genclose-args", lambda: GeneratorExit("g").args)
    show("empty-args-shared", lambda: (ValueError().args is ValueError().args))
    show("same-arg-tuple-identity", lambda: (lambda s: (lambda a, b: (a.args, b.args, a.args == b.args))(ValueError(s), ValueError(s)))(sys.intern("shared")))


def main():
    print(f"# {sys.implementation.name} {sys.version.split()[0]}")
    cases()


if __name__ == "__main__":
    main()
