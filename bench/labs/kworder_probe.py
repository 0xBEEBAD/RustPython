def posonly(a, b, /, c, d):
    return (a, b, c, d)
def varkw_pos(a, b, /, c, **kw):
    return (a, b, c, kw)
def cases():
    yield lambda: posonly(1, 2, 3, c=4, b=5)
    yield lambda: posonly(1, 2, 3, b=5, c=4)
    yield lambda: posonly(1, 2, 3, d=4, c=5)
    yield lambda: posonly(1, 2, 3, a=4, b=5)
    yield lambda: posonly(1, 2, 3, b=5, a=4)
    yield lambda: posonly(1, 2, 3, a=4, d=5)
    yield lambda: posonly(1, 2, c=3, d=4, a=5)
    yield lambda: varkw_pos(1, 2, 3, c=4, b=5)
    yield lambda: varkw_pos(1, 2, 3, b=5)
for i, fn in enumerate(cases()):
    try:
        print(i, "OK", fn())
    except TypeError as exc:
        print(i, "TypeError:", exc)
