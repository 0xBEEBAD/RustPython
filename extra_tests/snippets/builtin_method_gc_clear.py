import gc
import weakref

class Holder:
    pass

holder = Holder()
d = {}
d['owner'] = holder
holder.method = d.get
ref = weakref.ref(holder)
del holder, d
gc.collect()
assert ref() is None
print('ok')
