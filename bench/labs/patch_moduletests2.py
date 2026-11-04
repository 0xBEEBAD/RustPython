import io, re
path = 'crates/capi/src/moduleobject.rs'
with io.open(path, 'r', encoding='utf-8', newline='') as f:
    content = f.read()

# 1. tests 模块 import PyMethodPointer
content = content.replace(
    '    use crate::pystate::with_vm;',
    '    use crate::methodobject::PyMethodPointer;\n    use crate::pystate::with_vm;'
)
# 2. hello_fn 闭包类型标注
content = content.replace(
    '        with_vm(|vm| -> rustpython_vm::PyResult<_> {\n            Ok(vm.ctx.new_str("hello from C!").into())\n        })',
    '        with_vm(|vm| -> rustpython_vm::PyResult<rustpython_vm::PyObjectRef> {\n            Ok(vm.ctx.new_str("hello from C!").into())\n        })'
)
# 3. static → static mut(METHOD 和 DEF)
content = content.replace('static METHOD: PyMethodDef = PyMethodDef {', 'static mut METHOD: PyMethodDef = PyMethodDef {')
content = content.replace('static DEF: PyModuleDef = PyModuleDef {', 'static mut DEF: PyModuleDef = PyModuleDef {')
content = content.replace(
    '                let module_ptr = PyModule_Create(&DEF as *const PyModuleDef as *mut PyModuleDef);',
    '                let module_ptr = PyModule_Create(&mut DEF as *mut PyModuleDef);'
)
# 4. 指针转换到 pyo3 ffi
content = content.replace(
    '                let module: Py<pyo3::PyAny> = Py::from_owned_ptr(py, module_ptr);',
    '                let module: Py<pyo3::PyAny> =\n                    Py::from_owned_ptr(py, module_ptr as *mut pyo3::ffi::PyObject);'
)
with io.open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(content)
print('test fixes applied')
