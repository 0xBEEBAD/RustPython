//! The builtin `frozendict` type (PEP 814): an immutable, hashable mapping.
//!
//! Storage is the same [`DictContentType`](super::dict::DictContentType) used
//! by `dict`; the payload simply exposes no mutation operations. Mutating
//! helpers are only used on a temporary `PyDict` while a frozendict is being
//! constructed, before it becomes visible to Python code.

use super::{
    PyBaseExceptionRef, PyDict, PyDictRef, PyGenericAlias, PyTupleRef, PyType, PyTypeRef,
    dict::{
        PyDictItems, PyDictKeyIterator, PyDictKeys, PyDictReverseKeyIterator, PyDictValues,
    },
};
use crate::{
    AsObject, Context, Py, PyObject, PyObjectRef, PyPayload, PyRef, PyResult, atomic_func,
    builtins::dict::DictContentType,
    builtins::dict::mapping_unhashable_error,
    class::PyClassImpl,
    common::{
        hash::{self, FrozenSetHash, PyHash},
        wtf8::Wtf8Buf,
    },
    convert::ToPyObject,
    function::{ArgIterable, FuncArgs, KwArgs, OptionalArg, PyComparisonValue},
    protocol::{PyMappingMethods, PyNumberMethods, PySequenceMethods},
    recursion::ReprGuard,
    types::{
        AsMapping, AsNumber, AsSequence, Callable, Comparable, Constructor, Hashable, Initializer,
        Iterable, PyComparisonOp, Representable,
    },
    vm::VirtualMachine,
};
use core::fmt;
use rustpython_common::atomic::{Ordering, PyAtomic, Radium};

#[pyclass(module = false, name = "frozendict", traverse = "manual", clear)]
pub struct PyFrozenDict {
    entries: DictContentType,
    hash: PyAtomic<PyHash>,
}

impl Default for PyFrozenDict {
    fn default() -> Self {
        Self {
            entries: DictContentType::default(),
            hash: hash::SENTINEL.into(),
        }
    }
}

impl PyFrozenDict {
    pub(crate) fn new(entries: DictContentType) -> Self {
        Self {
            entries,
            hash: hash::SENTINEL.into(),
        }
    }

    pub(crate) const fn _as_frozen_entries(&self) -> &DictContentType {
        &self.entries
    }

    /// A regular `dict` snapshot with the same entries, used for the
    /// read-only views, `__getnewargs__` and `dict(fd)`.
    fn snapshot(&self, vm: &VirtualMachine) -> PyDictRef {
        PyDict::from_entries(self.entries.clone()).into_ref(&vm.ctx)
    }

    fn build(
        dict_obj: OptionalArg<PyObjectRef>,
        kwargs: KwArgs,
        vm: &VirtualMachine,
    ) -> PyResult<Self> {
        let tmp = PyDict::default();
        tmp.update(dict_obj, kwargs, vm)?;
        Ok(Self::new(tmp.into_entries()))
    }

    fn inner_getitem(&self, key: &PyObject, vm: &VirtualMachine) -> PyResult {
        match self
            .entries
            .get(vm, key)
            .map_err(|e| mapping_unhashable_error(vm, key, e, "frozendict"))?
        {
            Some(value) => Ok(value),
            None => Err(vm.new_key_error(key.to_owned())),
        }
    }

    fn entries_equal(&self, other: &DictContentType, vm: &VirtualMachine) -> PyResult<bool> {
        if self.entries.len() != other.len() {
            return Ok(false);
        }
        for (key, value) in self.entries.items() {
            let Some(other_value) = other
                .get(vm, &*key)
                .map_err(|e| mapping_unhashable_error(vm, &key, e, "frozendict"))?
            else {
                return Ok(false);
            };
            if value.is(&other_value) {
                continue;
            }
            if !vm.bool_eq(&value, &other_value)? {
                return Ok(false);
            }
        }
        Ok(true)
    }
}

unsafe impl crate::object::Traverse for PyFrozenDict {
    fn traverse(&self, traverse_fn: &mut crate::object::TraverseFn<'_>) {
        self.entries.traverse(traverse_fn);
    }

    fn clear(&mut self, out: &mut Vec<PyObjectRef>) {
        for (key, value) in self.entries.drain_entries() {
            out.push(key);
            out.push(value);
        }
    }
}

impl fmt::Debug for PyFrozenDict {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str("frozendict")
    }
}

impl PyPayload for PyFrozenDict {
    #[inline]
    fn class(ctx: &Context) -> &'static Py<PyType> {
        ctx.types.frozendict_type
    }
}

impl Constructor for PyFrozenDict {
    type Args = (OptionalArg<PyObjectRef>, KwArgs);

    fn slot_new(cls: PyTypeRef, args: FuncArgs, vm: &VirtualMachine) -> PyResult {
        // frozendict(frozendict) returns the same object for the exact type.
        if args.kwargs.is_empty()
            && args.args.len() == 1
            && cls.is(vm.ctx.types.frozendict_type)
            && args.args[0].class().is(vm.ctx.types.frozendict_type)
        {
            return Ok(args.args[0].clone());
        }
        let (dict_obj, kwargs): Self::Args = args.bind(vm)?;
        let payload = Self::build(dict_obj, kwargs, vm)?;
        payload.into_ref_with_type(vm, cls).map(Into::into)
    }

    fn py_new(
        _cls: &Py<PyType>,
        (dict_obj, kwargs): Self::Args,
        vm: &VirtualMachine,
    ) -> PyResult<Self> {
        Self::build(dict_obj, kwargs, vm)
    }
}

impl Initializer for PyFrozenDict {
    // CPython's frozendict has no tp_init of its own; object.__init__ ignores
    // excess arguments for types with a custom tp_new, so `fd.__init__(...)`
    // is a no-op.
    type Args = FuncArgs;

    fn init(_zelf: PyRef<Self>, _args: FuncArgs, _vm: &VirtualMachine) -> PyResult<()> {
        Ok(())
    }
}

#[pyclass(
    with(
        Constructor,
        Initializer,
        Comparable,
        Iterable,
        AsSequence,
        AsNumber,
        AsMapping,
        Hashable,
        Representable
    ),
    flags(BASETYPE, MAPPING, _MATCH_SELF)
)]
impl PyFrozenDict {
    fn __len__(&self) -> usize {
        self.entries.len()
    }

    #[pymethod]
    fn __sizeof__(&self) -> usize {
        crate::object::SIZEOF_PYOBJECT_HEAD + core::mem::size_of::<Self>() + self.entries.sizeof()
    }

    fn __contains__(&self, key: PyObjectRef, vm: &VirtualMachine) -> PyResult<bool> {
        self.entries
            .contains(vm, &*key)
            .map_err(|e| mapping_unhashable_error(vm, &key, e, "frozendict"))
    }

    fn __getitem__(&self, key: PyObjectRef, vm: &VirtualMachine) -> PyResult {
        self.inner_getitem(&key, vm)
    }

    #[pymethod]
    fn get(
        &self,
        key: PyObjectRef,
        default: OptionalArg<PyObjectRef>,
        vm: &VirtualMachine,
    ) -> PyResult {
        Ok(self
            .entries
            .get(vm, &*key)
            .map_err(|e| mapping_unhashable_error(vm, &key, e, "frozendict"))?
            .unwrap_or_else(|| default.unwrap_or_none(vm)))
    }

    #[pymethod]
    fn keys(zelf: PyRef<Self>, vm: &VirtualMachine) -> PyResult<PyDictKeys> {
        Ok(PyDictKeys::new(zelf.snapshot(vm)))
    }

    #[pymethod]
    fn values(zelf: PyRef<Self>, vm: &VirtualMachine) -> PyResult<PyDictValues> {
        Ok(PyDictValues::new(zelf.snapshot(vm)))
    }

    #[pymethod]
    fn items(zelf: PyRef<Self>, vm: &VirtualMachine) -> PyResult<PyDictItems> {
        Ok(PyDictItems::new(zelf.snapshot(vm)))
    }

    #[pymethod]
    fn __reversed__(zelf: PyRef<Self>, vm: &VirtualMachine) -> PyResult<PyDictReverseKeyIterator> {
        Ok(PyDictReverseKeyIterator::new(zelf.snapshot(vm)))
    }

    #[pymethod]
    fn copy(zelf: PyRef<Self>, vm: &VirtualMachine) -> PyRef<Self> {
        if zelf.class().is(vm.ctx.types.frozendict_type) {
            zelf
        } else {
            Self::new(zelf.entries.clone()).into_ref(&vm.ctx)
        }
    }

    fn __or__(zelf: PyRef<Self>, other: PyObjectRef, vm: &VirtualMachine) -> PyResult {
        if zelf.class().is(vm.ctx.types.frozendict_type) {
            // frozendict() | frozendict(...) => frozendict(...)
            if zelf.entries.len() == 0 && other.class().is(vm.ctx.types.frozendict_type) {
                return Ok(other);
            }
            // frozendict(...) | frozendict()/{} => frozendict(...)
            let other_is_empty = if other.class().is(vm.ctx.types.dict_type) {
                other
                    .downcast_ref::<PyDict>()
                    .is_some_and(|d| d.is_empty())
            } else if other.class().is(vm.ctx.types.frozendict_type) {
                other
                    .downcast_ref::<Self>()
                    .is_some_and(|d| d.__len__() == 0)
            } else {
                false
            };
            if other_is_empty {
                return Ok(zelf.into());
            }
        }

        let other_is_dict = other.downcast_ref::<PyDict>().is_some()
            || other.downcast_ref::<Self>().is_some();
        if !other_is_dict {
            return Ok(vm.ctx.not_implemented());
        }

        let tmp = PyDict::from_entries(zelf.entries.clone());
        tmp.merge_object(other, vm)?;
        Self::new(tmp.into_entries())
            .into_ref_with_type(vm, zelf.class().to_owned())
            .map(Into::into)
    }

    #[pymethod]
    fn __getnewargs__(&self, vm: &VirtualMachine) -> PyTupleRef {
        vm.new_tuple((self.snapshot(vm),))
    }

    #[pymethod]
    fn __reduce_ex__(zelf: PyRef<Self>, proto: usize, vm: &VirtualMachine) -> PyResult {
        if proto < 2 {
            return Err(vm.new_type_error("cannot pickle 'frozendict' object"));
        }
        let reduce_ex = vm
            .ctx
            .types
            .object_type
            .get_attr(identifier!(vm, __reduce_ex__))
            .expect("object.__reduce_ex__ must exist");
        reduce_ex.call((PyObjectRef::from(zelf), proto), vm)
    }

    #[pyclassmethod]
    fn fromkeys(
        class: PyTypeRef,
        iterable: ArgIterable,
        value: OptionalArg<PyObjectRef>,
        vm: &VirtualMachine,
    ) -> PyResult {
        let value = value.unwrap_or_none(vm);

        if class.is(vm.ctx.types.frozendict_type) {
            let tmp = PyDict::default();
            for key in iterable.iter(vm)? {
                tmp.inner_setitem(&*key?, value.clone(), vm)?;
            }
            return Self::new(tmp.into_entries())
                .into_ref_with_type(vm, class)
                .map(Into::into);
        }

        let result = PyType::call(&class, ().into(), vm)?;

        // A frozendict (or frozendict subclass) returned by the constructor:
        // build the keys into a mutable copy, then let the class construct
        // the final immutable object from it so constructor overrides run.
        let frozen_entries = result.downcast_ref::<Self>().map(|fd| fd.entries.clone());
        if let Some(entries) = frozen_entries {
            let tmp = PyDict::from_entries(entries);
            for key in iterable.iter(vm)? {
                tmp.inner_setitem(&*key?, value.clone(), vm)?;
            }
            let arg: PyObjectRef = Self::new(tmp.into_entries()).into_pyobject(vm);
            let args = FuncArgs {
                args: vec![arg],
                ..Default::default()
            };
            return PyType::call(&class, args, vm);
        }

        for key in iterable.iter(vm)? {
            result.set_item(&*key?, value.clone(), vm)?;
        }
        Ok(result)
    }

    #[pyclassmethod]
    fn __class_getitem__(
        cls: PyTypeRef,
        args: PyObjectRef,
        vm: &VirtualMachine,
    ) -> PyResult<PyGenericAlias> {
        PyGenericAlias::from_args(cls, args, vm)
    }
}

impl AsMapping for PyFrozenDict {
    fn as_mapping() -> &'static PyMappingMethods {
        static AS_MAPPING: PyMappingMethods = PyMappingMethods {
            length: atomic_func!(|mapping, _vm| Ok(PyFrozenDict::mapping_downcast(mapping)
                .__len__())),
            subscript: atomic_func!(|mapping, needle, vm| PyFrozenDict::mapping_downcast(mapping)
                .inner_getitem(needle, vm)),
            // No ass_subscript: item assignment is unsupported.
            ass_subscript: None,
        };
        &AS_MAPPING
    }
}

impl AsSequence for PyFrozenDict {
    fn as_sequence() -> &'static PySequenceMethods {
        static AS_SEQUENCE: PySequenceMethods = PySequenceMethods {
            contains: atomic_func!(|seq, target, vm| PyFrozenDict::sequence_downcast(seq)
                .entries
                .contains(vm, target)
                .map_err(|e| mapping_unhashable_error(vm, target, e, "frozendict"))),
            ..PySequenceMethods::NOT_IMPLEMENTED
        };
        &AS_SEQUENCE
    }
}

impl AsNumber for PyFrozenDict {
    fn as_number() -> &'static PyNumberMethods {
        // No inplace_or slot: `fd |= other` falls back to `fd = fd | other`,
        // matching CPython's frozendict.
        static AS_NUMBER: PyNumberMethods = PyNumberMethods {
            or: Some(|a, b, vm| {
                if let Some(a) = a.downcast_ref::<PyFrozenDict>() {
                    PyFrozenDict::__or__(a.to_owned(), b.to_pyobject(vm), vm)
                } else {
                    Ok(vm.ctx.not_implemented())
                }
            }),
            ..PyNumberMethods::NOT_IMPLEMENTED
        };
        &AS_NUMBER
    }
}

impl Comparable for PyFrozenDict {
    fn cmp(
        zelf: &Py<Self>,
        other: &PyObject,
        op: PyComparisonOp,
        vm: &VirtualMachine,
    ) -> PyResult<PyComparisonValue> {
        op.eq_only(|| {
            if let Some(other) = other.downcast_ref::<Self>() {
                return zelf
                    .entries_equal(&other.entries, vm)
                    .map(PyComparisonValue::Implemented);
            }
            if let Some(other) = other.downcast_ref::<PyDict>() {
                return zelf
                    .entries_equal(other._as_dict_inner(), vm)
                    .map(PyComparisonValue::Implemented);
            }
            Ok(PyComparisonValue::NotImplemented)
        })
    }
}

impl Hashable for PyFrozenDict {
    fn hash(zelf: &Py<Self>, vm: &VirtualMachine) -> PyResult<PyHash> {
        let cached = zelf.hash.load(Ordering::Relaxed);
        if cached != hash::SENTINEL {
            return Ok(cached);
        }

        let computed = vm
            .with_recursion("while hashing a frozendict", || {
                let mut hasher = FrozenSetHash::new(zelf.entries.len());
                for (key, key_hash, value) in zelf.entries.items_with_hashes() {
                    let _ = key;
                    let value_hash = value.hash(vm)?;
                    let pair_hash = hash::hash_tuple([
                        Ok::<PyHash, PyBaseExceptionRef>(key_hash),
                        Ok(value_hash),
                    ])?;
                    hasher.add(pair_hash);
                }
                Ok(hasher.finish())
            })
            .map_err(|err| {
                if err.fast_isinstance(vm.ctx.exceptions.recursion_error) {
                    vm.new_recursion_error(
                        "maximum recursion depth exceeded while hashing a frozendict",
                    )
                } else {
                    err
                }
            })?;

        let computed = hash::fix_sentinel(computed);
        match Radium::compare_exchange(
            &zelf.hash,
            hash::SENTINEL,
            computed,
            Ordering::Relaxed,
            Ordering::Relaxed,
        ) {
            Ok(_) => Ok(computed),
            Err(stored) => Ok(stored),
        }
    }
}

impl Iterable for PyFrozenDict {
    fn iter(zelf: PyRef<Self>, vm: &VirtualMachine) -> PyResult {
        Ok(PyDictKeyIterator::new(zelf.snapshot(vm)).into_pyobject(vm))
    }
}

impl Representable for PyFrozenDict {
    fn repr(zelf: &Py<Self>, vm: &VirtualMachine) -> PyResult<super::PyStrRef> {
        let class_name = {
            let name = zelf.class().name();
            name.to_string()
        };
        let s = if zelf.entries.len() == 0 {
            vm.ctx.new_str(format!("{class_name}()"))
        } else if let Some(_guard) = ReprGuard::enter(vm, zelf.as_object()) {
            let mut result = Wtf8Buf::from(format!("{class_name}("));
            result.push_char('{');
            let mut first = true;
            for (key, value) in zelf.entries.items() {
                if !first {
                    result.push_str(", ");
                }
                first = false;
                result.push_wtf8(key.repr(vm)?.as_wtf8());
                result.push_str(": ");
                result.push_wtf8(value.repr(vm)?.as_wtf8());
            }
            result.push_str("})");
            vm.ctx.new_str(result)
        } else {
            vm.ctx.new_str(format!("{class_name}({{...}})"))
        };
        Ok(s)
    }

    #[cold]
    fn repr_str(_zelf: &Py<Self>, _vm: &VirtualMachine) -> PyResult<String> {
        unreachable!("use repr instead")
    }
}

pub(crate) fn init(context: &'static Context) {
    PyFrozenDict::extend_class(context, context.types.frozendict_type);
}
