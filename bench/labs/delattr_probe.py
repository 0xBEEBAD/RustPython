class C:
    pass


for label, fn in (
    ("getattr", lambda: C.missing_fox),
    ("setattr", lambda: setattr(C, "missing_fox", 1)),
    ("delattr", lambda: delattr(C, "missing_fox")),
    ("instance getattr", lambda: C().missing_fox),
    ("instance setattr", lambda: setattr(C(), "missing_fox", 1)),
    ("instance delattr", lambda: delattr(C(), "missing_fox")),
):
    try:
        fn()
    except AttributeError as exc:
        print(
            f"{label:20s} name={exc.name!r} obj_is_type={getattr(exc, 'obj', None) is C}",
            str(exc)[:60],
        )
