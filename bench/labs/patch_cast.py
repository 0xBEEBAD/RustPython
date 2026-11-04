import io
path = 'crates/vm/src/stdlib/_ctypes/function.rs'
with io.open(path, 'r', encoding='utf-8', newline='') as f:
    lines = f.readlines()

insert_at = None
for i, l in enumerate(lines):
    if '} else if let Some(cdata) = obj.downcast_ref::<PyCData>()' in l:
        insert_at = i
        break
assert insert_at is not None, 'PyCData branch not found'
print('inserting before line', insert_at+1)

block = [
    '    } else if let Some(func_ptr) = obj.downcast_ref::<PyCFuncPtr>() {\n',
    '        // Callback instance: cast to the stored function pointer\n',
    '        // (CPython casts CFuncPtr to the pointer value in its buffer).\n',
    '        func_ptr.get_func_ptr()\n',
    '    } else if let Some(carg) = obj.downcast_ref::<CArgObject>() {\n',
    '        // byref() result: use the stored pointer value\n',
    '        match &carg.value {\n',
    '            CArgValue::Pointer(p) => *p,\n',
    '            _ => {\n',
    '                return Err(vm.new_type_error(\n',
    '                    "cast() argument 1 must be a pointer-like ctypes instance",\n',
    '                ));\n',
    '            }\n',
    '        }\n',
]
lines[insert_at:insert_at] = block
with io.open(path, 'w', encoding='utf-8', newline='') as f:
    f.writelines(lines)
print('cast branches added')
