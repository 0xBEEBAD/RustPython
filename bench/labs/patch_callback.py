import io
path = 'crates/vm/src/stdlib/_ctypes/function.rs'
with io.open(path, 'r', encoding='utf-8', newline='') as f:
    lines = f.readlines()

# 1. conv_param:在步骤 3(paramfunc)之后插入 PyCFuncPtr 分支
anchor1 = None
for i, l in enumerate(lines):
    if '// 3. ctypes objects -> use paramfunc' in l:
        anchor1 = i
        break
assert anchor1 is not None
# 找到该块结束(paramfunc 块的闭合,即 "    }\n\n    // 4." 之间)
end1 = None
for i in range(anchor1, len(lines)):
    if '// 4. Python str -> wide string pointer' in l if False else '// 4. Python str -> wide string pointer' in lines[i]:
        end1 = i
        break
assert end1 is not None
block1 = [
    '    // 3b. PyCFuncPtr (callback) -> function pointer value; keep the\n',
    '    //      callable alive for the duration of the foreign call.\n',
    '    if let Some(func_ptr) = value.downcast_ref::<PyCFuncPtr>() {\n',
    '        let addr = func_ptr.get_func_ptr();\n',
    '        return Ok(Argument {\n',
    '            keep: Some(value.to_owned()),\n',
    '            value: CArgValue::pointer(addr),\n',
    '        });\n',
    '    }\n',
    '\n',
]
lines[end1:end1] = block1
print('conv_param patched at', end1+1)

# 2. convert_object:在 pointer 类型处理(257 行 "// For pointer types (POINTER(T))")之前插入
anchor2 = None
for i, l in enumerate(lines):
    if '// For pointer types (POINTER(T)), we need to pass the pointer VALUE stored in buffer' in l:
        anchor2 = i
        break
assert anchor2 is not None
block2 = [
    '        // PyCFuncPtr (callback) -> function pointer value\n',
    '        if let Some(func_ptr) = converted.downcast_ref::<PyCFuncPtr>() {\n',
    '            return Ok((\n',
    '                CArgValue::pointer(func_ptr.get_func_ptr()),\n',
    '                Some(converted.clone()),\n',
    '            ));\n',
    '        }\n',
    '\n',
]
lines[anchor2:anchor2] = block2
print('convert_object patched at', anchor2+1)

with io.open(path, 'w', encoding='utf-8', newline='') as f:
    f.writelines(lines)
print('done')
