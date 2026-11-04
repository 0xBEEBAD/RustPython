import io
path = 'crates/vm/src/builtins/type.rs'
with io.open(path, 'r', encoding='utf-8', newline='') as f:
    lines = f.readlines()

# 找 "// Check if slot name conflicts with class attributes" 块
idx = None
for i, l in enumerate(lines):
    if 'Check if slot name conflicts with class attributes' in l:
        idx = i
        break
assert idx is not None, 'marker not found'
# 块:注释行 + if 语句(4 行)+ 闭合
# 结构:
#   // Check if slot name conflicts with class attributes
#   if attributes.contains_key(vm.ctx.intern_str(slot.as_wtf8())) {
#       return Err(vm.new_value_error(format!(
#           "'{}' in __slots__ conflicts with class variable",
#           slot.as_wtf8()
#       )));
#   }
# 找 if 行和结束
if_idx = None
for i in range(idx, min(idx + 10, len(lines))):
    if 'if attributes.contains_key(vm.ctx.intern_str(slot.as_wtf8()))' in lines[i]:
        if_idx = i
        break
assert if_idx is not None
# 找闭合 }(后面是空行或下一注释)
end_idx = None
for i in range(if_idx + 1, min(if_idx + 10, len(lines))):
    if lines[i].strip() == '}':
        end_idx = i
        break
assert end_idx is not None
print('block lines', if_idx + 1, '..', end_idx + 1)

new_block = [
    '                // Check if slot name conflicts with class attributes.\n',
    '                // __dict__ and __weakref__ are special slots: CPython does not\n',
    '                // treat a same-named class attribute as a conflict for them\n',
    '                // (celery\'s Proxy class defines __slots__ containing\n',
    "                // '__dict__' alongside a __dict__ property).\n",
    '                if slot_name != b"__dict__"\n',
    '                    && slot_name != b"__weakref__"\n',
    '                    && attributes.contains_key(vm.ctx.intern_str(slot.as_wtf8()))\n',
    '                {\n',
    '                    return Err(vm.new_value_error(format!(\n',
    "                        \"'{}' in __slots__ conflicts with class variable\",\n",
    '                        slot.as_wtf8()\n',
    '                    )));\n',
    '                }\n',
]
lines[idx:end_idx+1] = new_block
with io.open(path, 'w', encoding='utf-8', newline='') as f:
    f.writelines(lines)
print('patched OK')
