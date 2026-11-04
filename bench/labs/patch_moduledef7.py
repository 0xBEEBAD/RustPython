import io
path = 'crates/capi/src/moduleobject.rs'
with io.open(path, 'r', encoding='utf-8', newline='') as f:
    content = f.read()
content = content.replace(
    'use rustpython_vm::{PyObjectRef, builtins::{PyModule, PyStr}};',
    'use rustpython_vm::{AsObject, PyObjectRef, builtins::{PyModule, PyStr}};'
)
with io.open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(content)
print('AsObject import added')
