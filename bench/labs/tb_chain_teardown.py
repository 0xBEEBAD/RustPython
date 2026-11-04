"""Does the interpreter survive dropping a long __traceback__ chain at teardown?

`raise e` on the same exception object appends one PyTraceback per iteration, so
the chain is N links long. CPython releases it inside a trashcan and exits 0;
RustPython's drop walks `next` recursively and overflows the native stack.

Modes:
  keep   - hold the exception until the interpreter tears down (the crash)
  drop   - release it explicitly inside the program (already survives)
  gc     - release it through a collected reference cycle (same crash path,
           reachable while the program is still running)

Why `drop` survives but `gc` does not: the collector untracks an object it has
judged truly_dead *before* dropping it, and the trashcan only engages for
tracked objects - so a cycle-freed chain drops unguarded, exactly like the
chain the interpreter frees at teardown.
"""

import sys

mode = sys.argv[1] if len(sys.argv) > 1 else "keep"
n = int(sys.argv[2]) if len(sys.argv) > 2 else 50_000

e = ValueError("boom")
for _ in range(n):
    try:
        raise e
    except ValueError:
        pass

tb_depth = 0
cur = e.__traceback__
while cur is not None:
    tb_depth += 1
    cur = cur.tb_next

ctx_depth = 0
cur = e.__context__
while cur is not None:
    ctx_depth += 1
    cur = cur.__context__

print(f"traceback links: {tb_depth}  context links: {ctx_depth}  raises: {n}")

if mode == "drop":
    del e
    print("dropped inside the program")

if mode == "gc":
    holder = []
    holder.append(holder)
    holder.append(e)
    del e
    import gc

    gc.collect()
    print("collected through gc")

print("reached end of script; teardown follows")
