import sys
sys.path.insert(0, r'C:\Dev2\luna-lang\RustPython\bench\labs\sitepkg')
from celery import Celery
app = Celery("tasks", broker="memory://", result_backend="cache+memory://")
@app.task
def add(x, y):
    return x + y
# 直接调用(任务函数本身)
print("direct call:", add(2, 3))
# 异步调用
r = add.delay(4, 5)
print("delayed task:", r.get(timeout=10))
print("celery OK")
