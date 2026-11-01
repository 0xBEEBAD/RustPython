//! The builtin `sentinel` type (CPython 3.15, PEP 661 as implemented in
//! gh-148829): unique marker objects with a concise representation.
//!
//! Shape taken from `Objects/sentinelobject.c` of the 3.15 tree:
//! `sentinel(name, /, *, repr=None)` records the *calling* module, prints as
//! `repr` when given and otherwise as the bare name, keeps identity through
//! `copy`/`deepcopy`, reduces to its name so pickle resolves it as a module
//! global, and participates in type expressions because `|` accepts sentinels.
//!
//! Comparison, hashing and the refusal to be subclassed are left to the
//! defaults: native classes are immutable-typed and carry no BASETYPE, and
//! `object` supplies identity equality plus a pointer hash - which is exactly
//! CPython's `_Py_BaseObject_RichCompare` + `PyObject_GenericHash` pair.

use super::{PyStr, PyStrRef, PyType, PyTypeRef};
use crate::{
    AsObject, Context, Py, PyObjectRef, PyPayload, PyRef, PyResult,
    class::PyClassImpl,
    common::lock::PyMutex,
    function::{FuncArgs, PySetterValue},
    object::{Traverse, TraverseFn},
    protocol::PyNumberMethods,
    types::{AsNumber, Constructor, Representable},
    vm::VirtualMachine,
};

#[pyclass(module = false, name = "sentinel", traverse = "manual")]
#[derive(Debug)]
pub struct PySentinel {
    name: PyStrRef,
    /// The module of the frame that created the sentinel, which together with
    /// `__name__` is what makes it addressable as `module.name` for pickle.
    /// `del` clears it and reading it afterwards fails like any missing
    /// attribute - CPython's `Py_T_OBJECT_EX` behaviour.
    module: PyMutex<Option<PyObjectRef>>,
    custom_repr: Option<PyStrRef>,
}

unsafe impl Traverse for PySentinel {
    fn traverse(&self, tracer_fn: &mut TraverseFn<'_>) {
        self.name.traverse(tracer_fn);
        self.module.traverse(tracer_fn);
        self.custom_repr.traverse(tracer_fn);
    }
}

impl PyPayload for PySentinel {
    #[inline]
    fn class(ctx: &Context) -> &'static Py<PyType> {
        ctx.types.sentinel_type
    }
}

impl Constructor for PySentinel {
    type Args = ();

    // Bound by hand because `name` is positional-only; the derive-based binder
    // would accept `sentinel(name="X")`, which CPython rejects.
    fn slot_new(cls: PyTypeRef, args: FuncArgs, vm: &VirtualMachine) -> PyResult {
        // `name` is positional-only, so the positional list is consumed by hand
        // and any keyword named `name` is a failure rather than a binding.
        let mut positional = args.args.into_iter();
        let mut kwargs = args.kwargs;
        let name = match positional.next() {
            None => {
                return Err(vm.new_type_error("sentinel() takes exactly one argument (0 given)"));
            }
            Some(name) => name.downcast::<PyStr>().map_err(|name| {
                vm.new_type_error(format!(
                    "sentinel() argument 'name' must be str, not {}",
                    name.class().name()
                ))
            })?,
        };
        if positional.next().is_some() {
            return Err(vm.new_type_error(
                "sentinel() takes at most 1 positional argument (2 given)",
            ));
        }
        if kwargs.contains_key("name") {
            return Err(vm.new_type_error(
                "sentinel() got some positional-only arguments passed as keyword arguments: 'name'",
            ));
        }
        let custom_repr = match kwargs.swap_remove("repr") {
            None => None,
            Some(value) if vm.is_none(&value) => None,
            Some(value) => Some(value.downcast::<PyStr>().map_err(|value| {
                vm.new_type_error(format!(
                    "sentinel() argument 'repr' must be str or None, not {}",
                    value.class().name()
                ))
            })?),
        };
        if let Some(key) = kwargs.keys().next() {
            return Err(vm.new_type_error(format!(
                "sentinel() got an unexpected keyword argument '{key}'"
            )));
        }
        let sentinel = PySentinel {
            name,
            module: PyMutex::new(Some(caller_module(vm))),
            custom_repr,
        };
        sentinel.into_ref_with_type(vm, cls).map(Into::into)
    }

    fn py_new(_cls: &Py<PyType>, _args: Self::Args, _vm: &VirtualMachine) -> PyResult<Self> {
        unreachable!("sentinel binds its arguments in slot_new")
    }
}

/// `PyFunction_GetModule` of the frame that called `sentinel()`, which is the
/// current frame while a C-level constructor runs. None outside any Python
/// frame (and for a module-level frame that has no `__name__`).
fn caller_module(vm: &VirtualMachine) -> PyObjectRef {
    let Some(frame) = vm.current_frame() else {
        return vm.ctx.none();
    };
    match frame
        .iframe()
        .globals()
        .get_item_opt(identifier!(vm, __name__), vm)
    {
        Ok(Some(name)) => name,
        _ => vm.ctx.none(),
    }
}

#[pyclass(with(Constructor, AsNumber, Representable))]
impl PySentinel {
    #[pygetset]
    fn __name__(zelf: &Py<Self>) -> PyStrRef {
        zelf.name.clone()
    }

    #[pygetset]
    fn __module__(zelf: &Py<Self>, vm: &VirtualMachine) -> PyResult<PyObjectRef> {
        zelf.module
            .lock()
            .clone()
            .ok_or_else(|| vm.new_attribute_error("__module__"))
    }

    #[pygetset(setter)]
    fn set___module__(zelf: &Py<Self>, value: PySetterValue) {
        *zelf.module.lock() = match value {
            PySetterValue::Assign(value) => Some(value),
            PySetterValue::Delete => None,
        };
    }

    #[pymethod]
    fn __copy__(zelf: PyRef<Self>) -> PyRef<Self> {
        zelf
    }

    #[pymethod]
    fn __deepcopy__(zelf: PyRef<Self>, _memo: PyObjectRef) -> PyRef<Self> {
        zelf
    }

    #[pymethod]
    fn __reduce__(zelf: &Py<Self>) -> PyStrRef {
        zelf.name.clone()
    }
}

impl Representable for PySentinel {
    #[inline]
    fn repr(zelf: &Py<Self>, _vm: &VirtualMachine) -> PyResult<PyStrRef> {
        Ok(zelf.custom_repr.clone().unwrap_or_else(|| zelf.name.clone()))
    }

    #[cold]
    fn repr_str(_zelf: &Py<Self>, _vm: &VirtualMachine) -> PyResult<String> {
        unreachable!("use repr instead")
    }
}

impl AsNumber for PySentinel {
    fn as_number() -> &'static PyNumberMethods {
        static AS_NUMBER: PyNumberMethods = PyNumberMethods {
            or: Some(|zelf, other, vm| {
                crate::builtins::union_::or_op(zelf.to_owned().into(), other.to_owned().into(), vm)
            }),
            ..PyNumberMethods::NOT_IMPLEMENTED
        };
        &AS_NUMBER
    }
}

pub(crate) fn init(context: &'static Context) {
    PySentinel::extend_class(context, context.types.sentinel_type);
}
