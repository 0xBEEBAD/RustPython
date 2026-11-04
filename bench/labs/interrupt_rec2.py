import faulthandler
import time
import threading
import _thread

faulthandler.dump_traceback_later(6, exit=True)


def f():
    try:
        f()
    except RecursionError:
        f()


def g():
    try:
        raise ValueError()
    except* ValueError:
        f()


def h():
    time.sleep(1)
    print("interrupting", flush=True)
    _thread.interrupt_main()


t = threading.Thread(target=h)
t.start()
g()
t.join()
print("done", flush=True)
