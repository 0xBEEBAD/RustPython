import sys
sys.path.insert(0, r'C:\Dev2\luna-lang\RustPython\bench\labs\sitepkg')
from celery import Celery
app = Celery("tasks", broker="memory://")
app.conf.task_always_eager = True
@app.task
def add(x, y):
    return x + y
r = add.delay(2, 3)
print("eager:", r.get())
c = (add.s(2, 3) | add.s(10))
res = c()
print("chain type:", type(res), "result:", res.get() if hasattr(res, "get") else res)
