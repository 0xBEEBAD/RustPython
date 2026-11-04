import io
path = 'crates/capi/src/moduleobject.rs'
with io.open(path, 'r', encoding='utf-8', newline='') as f:
    lines = f.readlines()

# 在文件末尾追加 PyModuleDef 实现
new_code = '''
// ---------------------------------------------------------------------------
// PyModuleDef / PyModule_Create (CPython Modules/moduleobject.c, import.c)
//
// Layouts mirror CPython's Include/cpython/moduleobject.h exactly so that
// extensions compiled against CPython headers (including pyo3 abi3 output)
// can pass their PyModuleDef to us.
// ---------------------------------------------------------------------------

/// PyObject_HEAD is opaque here: extensions allocate the base with CPython's
/// header, and we only touch fields at CPython offsets.
#[repr(C)]
pub struct PyModuleDefBase {
    pub ob_head: [usize; 2], // ob_refcnt, ob_type (PyObject_HEAD)
    pub m_init: Option<unsafe extern "C" fn() -> *mut PyObject>,
    pub m_index: isize,
    pub m_copy: *mut PyObject,
}

#[repr(C)]
pub struct PyModuleDef_Slot {
    pub slot: c_int,
    pub value: *mut c_void,
}

#[repr(C)]
pub struct PyModuleDef {
    pub m_base: PyModuleDefBase,
    pub m_name: *const c_char,
    pub m_doc: *const c_char,
    pub m_size: isize,
    pub m_methods: *const PyMethodDef,
    pub m_slots: *const PyModuleDef_Slot,
    pub m_traverse:
        Option<unsafe extern "C" fn(*mut PyObject, *mut c_void, *mut c_void) -> c_int>,
    pub m_clear: Option<unsafe extern "C" fn(*mut PyObject) -> c_int>,
    pub m_free: Option<unsafe extern "C" fn(*mut PyObject)>,
}

pub const Py_mod_create: c_int = 1;
pub const Py_mod_exec: c_int = 2;
pub const Py_mod_multiple_interpreters: c_int = 3;

static MODULE_INDEX: core::sync::atomic::AtomicIsize =
    core::sync::atomic::AtomicIsize::new(0);

/// PyModuleDef_Init: assign a unique m_index and return the def as an object.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn PyModuleDef_Init(def: *mut PyModuleDef) -> *mut PyObject {
    if def.is_null() {
        return core::ptr::null_mut();
    }
    let def = unsafe { &mut *def };
    if def.m_base.m_index == -1 {
        def.m_base.m_index = MODULE_INDEX.fetch_add(1, core::sync::atomic::Ordering::Relaxed);
    }
    def.cast::<PyObject>()
}

/// PyModule_Create: build a module from a PyModuleDef (methods + slots).
#[unsafe(no_mangle)]
pub unsafe extern "C" fn PyModule_Create(def: *mut PyModuleDef) -> *mut PyObject {
    unsafe { _PyModule_Create(def) }
}

#[unsafe(no_mangle)]
pub unsafe extern "C" fn _PyModule_Create(def: *mut PyModuleDef) -> *mut PyObject {
    with_vm(|vm| -> rustpython_vm::PyResult<_> {
        if def.is_null() {
            return Err(vm.new_system_error("PyModule_Create called with a null def"));
        }
        if PyModuleDef_Init(def).is_null() {
            return Err(vm.new_system_error("PyModuleDef_Init failed"));
        }
        let def = unsafe { &*def };
        let name = unsafe { def.m_name.try_as_str(vm) }?;

        // 1. Py_mod_create slot or a plain new module.
        let mut module: PyObjectRef = if !def.m_slots.is_null() {
            let slot_count = unsafe { module_slot_count(def.m_slots) };
            let slots = unsafe { core::slice::from_raw_parts(def.m_slots, slot_count) };
            if let Some(slot) = slots.iter().find(|s| s.slot == Py_mod_create) {
                let create: Option<
                    unsafe extern "C" fn(*mut PyObject, *mut c_void) -> *mut PyObject,
                > = unsafe { core::mem::transmute(slot.value) };
                let created = create.map_or(core::ptr::null_mut(), |f| {
                    unsafe { f(def.cast::<PyObject>(), core::ptr::null_mut()) }
                });
                if created.is_null() {
                    return Err(vm.new_system_error("Py_mod_create returned NULL"));
                }
                unsafe { &*created }.to_owned()
            } else {
                vm.new_module(name, vm.ctx.new_dict(), None).into()
            }
        } else {
            vm.new_module(name, vm.ctx.new_dict(), None).into()
        };

        // 2. Add the method table.
        if !def.m_methods.is_null() {
            let method_count = unsafe { method_def_count(def.m_methods) };
            let methods = unsafe { core::slice::from_raw_parts(def.m_methods, method_count) };
            let dict = module
                .downcast_ref::<PyModule>(vm)
                .ok_or_else(|| vm.new_system_error("module object is not a module"))?
                .dict();
            for md in methods {
                let method = build_method_def(vm, md, false)?;
                dict.set_item(
                    rustpython_vm::identifier!(vm, __name__) /* placeholder */,
                    method.into(),
                    vm,
                )
                .map_err(|e| vm.new_system_error(format!("cannot add method: {e}")))?;
            }
        }

        // 3. Py_mod_exec slot.
        if !def.m_slots.is_null() {
            let slot_count = unsafe { module_slot_count(def.m_slots) };
            let slots = unsafe { core::slice::from_raw_parts(def.m_slots, slot_count) };
            if let Some(slot) = slots.iter().find(|s| s.slot == Py_mod_exec) {
                let exec: Option<unsafe extern "C" fn(*mut PyObject) -> c_int> =
                    unsafe { core::mem::transmute(slot.value) };
                if let Some(f) = exec {
                    let rc = unsafe { f(module.as_raw().as_ptr()) };
                    if rc < 0 {
                        return Err(vm.new_system_error("Py_mod_exec failed"));
                    }
                }
            }
        }

        Ok(module)
    })
}

unsafe fn method_def_count(methods: *const PyMethodDef) -> usize {
    let mut n = 0;
    loop {
        let md = unsafe { &*methods.add(n) };
        if md.ml_name.is_null() {
            return n;
        }
        n += 1;
    }
}

unsafe fn module_slot_count(slots: *const PyModuleDef_Slot) -> usize {
    let mut n = 0;
    loop {
        let slot = unsafe { &*slots.add(n) };
        if slot.slot == 0 {
            return n;
        }
        n += 1;
    }
}
'''
with io.open(path, 'a', encoding='utf-8', newline='') as f:
    f.write(new_code)
print('PyModuleDef implementation appended')

# 更新 imports
content = io.open(path, 'r', encoding='utf-8', newline='').read()
old_imports = 'use crate::PyObject;\nuse crate::object::define_py_check;\nuse crate::pystate::with_vm;\nuse rustpython_vm::builtins::{PyModule, PyStr};'
new_imports = '''use crate::PyObject;
use crate::methodobject::{PyMethodDef, build_method_def};
use crate::object::define_py_check;
use crate::pystate::with_vm;
use crate::util::CStrExt;
use core::ffi::{c_char, c_int, c_void};
use rustpython_vm::builtins::{PyModule, PyStr};'''
if old_imports in content:
    content = content.replace(old_imports, new_imports)
    io.open(path, 'w', encoding='utf-8', newline='').write(content)
    print('imports updated')
else:
    print('imports pattern not found, checking current head')
    print(content[:400])
