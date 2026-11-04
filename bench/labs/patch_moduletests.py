import io
path = 'crates/capi/src/moduleobject.rs'
with io.open(path, 'r', encoding='utf-8', newline='') as f:
    content = f.read()

test_code = '''
#[cfg(test)]
mod tests {
    use super::*;
    use crate::pystate::with_vm;
    use core::ffi::c_int;
    use pyo3::prelude::*;
    use rustpython_vm::function::PyMethodFlags;

    unsafe extern "C" fn hello_fn(_slf: *mut PyObject, _args: *mut PyObject) -> *mut PyObject {
        with_vm(|vm| -> rustpython_vm::PyResult<_> {
            Ok(vm.ctx.new_str("hello from C!").into())
        })
    }

    #[test]
    fn module_create_with_methods() {
        Python::attach(|py| {
            unsafe {
                static METHOD: PyMethodDef = PyMethodDef {
                    ml_name: c"hello".as_ptr(),
                    ml_meth: PyMethodPointer {
                        PyCFunction: hello_fn,
                    },
                    ml_flags: PyMethodFlags::NOARGS.bits() as c_int,
                    ml_doc: c"say hello".as_ptr(),
                };
                static DEF: PyModuleDef = PyModuleDef {
                    m_base: PyModuleDefBase {
                        ob_head: [0; 2],
                        m_init: None,
                        m_index: -1,
                        m_copy: core::ptr::null_mut(),
                    },
                    m_name: c"testmod".as_ptr(),
                    m_doc: core::ptr::null(),
                    m_size: 0,
                    m_methods: &METHOD as *const PyMethodDef,
                    m_slots: core::ptr::null(),
                    m_traverse: None,
                    m_clear: None,
                    m_free: None,
                };
                let module_ptr = PyModule_Create(&DEF as *const PyModuleDef as *mut PyModuleDef);
                assert!(!module_ptr.is_null(), "PyModule_Create returned NULL");
                let module: Py<pyo3::PyAny> = Py::from_owned_ptr(py, module_ptr);
                let name: String = module.getattr(py, "__name__").unwrap().extract(py).unwrap();
                assert_eq!(name, "testmod");
                let hello = module.getattr(py, "hello").unwrap();
                let result: String = hello.call0(py).unwrap().extract(py).unwrap();
                assert_eq!(result, "hello from C!");
            }
        });
    }

    #[test]
    fn module_def_init_assigns_index() {
        Python::attach(|_py| {
            unsafe {
                static mut DEF: PyModuleDef = PyModuleDef {
                    m_base: PyModuleDefBase {
                        ob_head: [0; 2],
                        m_init: None,
                        m_index: -1,
                        m_copy: core::ptr::null_mut(),
                    },
                    m_name: c"idxmod".as_ptr(),
                    m_doc: core::ptr::null(),
                    m_size: 0,
                    m_methods: core::ptr::null(),
                    m_slots: core::ptr::null(),
                    m_traverse: None,
                    m_clear: None,
                    m_free: None,
                };
                let ptr = PyModuleDef_Init(&mut DEF as *mut PyModuleDef);
                assert!(!ptr.is_null());
                assert_ne!(DEF.m_base.m_index, -1);
            }
        });
    }
}
'''
with io.open(path, 'a', encoding='utf-8', newline='') as f:
    f.write(test_code)
print('tests appended')
