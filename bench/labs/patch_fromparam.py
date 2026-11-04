import io
path = 'crates/vm/src/stdlib/_ctypes/function.rs'
with io.open(path, 'r', encoding='utf-8', newline='') as f:
    lines = f.readlines()

# 在 PyCFuncPtrType impl 里加 from_param(在 __pointer_type__ setter 之后)
anchor = None
for i, l in enumerate(lines):
    if 'fn set_pointer_type(zelf: PyTypeRef, value: PyObjectRef, vm: &VirtualMachine) -> PyResult<()> {' in l:
        anchor = i
        break
assert anchor is not None
# 找该函数结束
depth = 0
end = None
for i in range(anchor, len(lines)):
    depth += lines[i].count('{') - lines[i].count('}')
    if depth == 0 and i > anchor:
        end = i
        break
assert end is not None
print('anchor fn ends at', end+1)

new_block = [
    '\n',
    '    /// from_param: CPython\'s CFuncPtr types expose from_param so the\n',
    '    /// callback instance (carrying the function pointer) can be passed\n',
    '    /// directly as an argument; _ctypes extracts the pointer when\n',
    '    /// building the call.\n',
    '    #[pyclassmethod]\n',
    '    fn from_param(cls: PyTypeRef, value: PyObjectRef, vm: &VirtualMachine) -> PyResult {\n',
    '        if value.downcast_ref::<PyCFuncPtr>().is_some() {\n',
    '            Ok(value)\n',
    '        } else {\n',
    '            Err(vm.new_type_error(format!(\n',
    '                "cannot convert \'{}\' to this function pointer type",\n',
    '                value.class().name()\n',
    '            )))\n',
    '        }\n',
    '    }\n',
]
lines[end+1:end+1] = new_block
with io.open(path, 'w', encoding='utf-8', newline='') as f:
    f.writelines(lines)
print('from_param added')
