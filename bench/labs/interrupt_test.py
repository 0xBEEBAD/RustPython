import time
import threading
import _thread


def h():
    time.sleep(0.5)
    print("interrupting", flush=True)
    _thread.interrupt_main()


t = threading.Thread(target=h)
t.start()
n = 0
while True:
    n += 1
