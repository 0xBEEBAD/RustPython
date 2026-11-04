class C:
    pass


def show(label, fn):
    try:
        fn()
    except AttributeError as exc:
        print(f"{label:22s} name={exc.name!r} obj={type(getattr(exc, 'obj', None)).__name__} msg={str(exc)[:52]}")
    else:
        print(f"{label:22s} no AttributeError")


show("class delattr", lambda: delattr(C, "missing_fox"))
show("instance delattr", lambda: delattr(C(), "missing_fox"))
show("instance setattr", lambda: setattr(C(), 1, 2))
