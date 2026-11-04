import io
path = 'crates/capi/src/moduleobject.rs'
with io.open(path, 'r', encoding='utf-8', newline='') as f:
    content = f.read()

content = content.replace(
    'use rustpython_vm::builtins::{PyModule, PyStr};',
    'use rustpython_vm::{PyObjectRef, builtins::{PyModule, PyStr}};'
)
content = content.replace('    def.cast::<PyObject>()', '    def as *mut PyModuleDef as *mut PyObject')
content = content.replace('unsafe { f(def.cast::<PyObject>(), core::ptr::null_mut()) }',
                          'unsafe { f(def as *const PyModuleDef as *mut PyObject, core::ptr::null_mut()) }')
with io.open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(content)
print('fixes applied')
