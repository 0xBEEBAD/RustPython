import traceback


class Addition:
    noise = more_noise = a = bc = None
    bluchin = None


def attempt():
    delattr(Addition(), "bluch")


try:
    attempt()
except AttributeError as exc:
    print("name:", repr(exc.name), "obj:", type(exc.obj).__name__)
    print("line:", traceback.format_exception(type(exc), exc, exc.__traceback__)[-1].rstrip())
