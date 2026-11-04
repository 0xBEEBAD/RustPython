import io
path = 'crates/capi/src/moduleobject.rs'
with io.open(path, 'r', encoding='utf-8', newline='') as f:
    lines = f.readlines()

# 行级更新 imports(前 4 行)
lines[0] = 'use crate::PyObject;\n'
lines[1] = 'use crate::methodobject::{PyMethodDef, build_method_def};\n'
lines[2] = 'use crate::object::define_py_check;\n'
lines[3] = 'use crate::pystate::with_vm;\n'
lines[4] = 'use crate::util::CStrExt;\n'
lines[5] = 'use core::ffi::{c_char, c_int, c_void};\n'
lines[6] = 'use rustpython_vm::builtins::{PyModule, PyStr};\n'
with io.open(path, 'w', encoding='utf-8', newline='') as f:
    f.writelines(lines)
print('imports rewritten')
