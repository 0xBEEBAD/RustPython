import io
path = 'crates/vm/src/stdlib/_ctypes/base.rs'
with io.open(path, 'r', encoding='utf-8', newline='') as f:
    lines = f.readlines()

# descr_set 里的 cdata.set_field( 调用:找 "fn descr_set" 之后的所有 set_field 调用,取最后一个
sites = []
in_descr_set = False
for i, l in enumerate(lines):
    if 'fn descr_set' in l:
        in_descr_set = True
    if in_descr_set and 'cdata.set_field(' in l:
        sites.append(i)
print('descr_set call sites:', sites)
assert sites, 'no set_field call in descr_set'
start = sites[-1]
# 找到调用结束
depth = 1
end = start
j = start + 1
while j < len(lines):
    d = lines[j].count('(') - lines[j].count(')')
    depth += d
    if depth == 0:
        end = j
        break
    j += 1
call_text = ''.join(lines[start:end+1])
print('--- current call ---')
print(call_text)

# 构造新代码:用 if/else 包住调用
indent = '                '
new_block = [
    '                if zelf.bitfield_size > 0 {\n',
    '                    // Read-modify-write the storage unit: clear the bitfield,\n',
    '                    // OR in the masked new value (matching CPython\'s b_set).\n',
    '                    let bits = zelf.bitfield_size as u32;\n',
    '                    let shift = zelf.bit_offset_val as u32;\n',
    '                    let mask = (1u64 << bits) - 1;\n',
    '                    let current = cdata.get_field(\n',
    '                        zelf.proto.as_object(),\n',
    '                        zelf.index,\n',
    '                        size,\n',
    '                        offset,\n',
    '                        obj.clone(),\n',
    '                        vm,\n',
    '                    )?;\n',
    '                    let cur = crate::builtins::int::get_value(&current)\n',
    '                        .to_i64()\n',
    '                        .ok_or_else(|| vm.new_type_error("bitfield storage is not an int"))?\n',
    '                        as u64;\n',
    '                    let new_val = crate::builtins::int::get_value(&value)\n',
    '                        .to_i64()\n',
    '                        .ok_or_else(|| vm.new_type_error("bitfield value is not an int"))?\n',
    '                        as u64;\n',
    '                    let merged = (cur & !(mask << shift)) | ((new_val & mask) << shift);\n',
    '                    // PyCData_set\n',
    '                    cdata.set_field(\n',
    '                        zelf.proto.as_object(),\n',
    '                        vm.ctx.new_int(merged).into(),\n',
    '                        zelf.index,\n',
    '                        size,\n',
    '                        offset,\n',
    '                        needs_swap,\n',
    '                        vm,\n',
    '                    )\n',
    '                } else {\n',
    '                    // PyCData_set\n',
    '                    cdata.set_field(\n',
    '                        zelf.proto.as_object(),\n',
    '                        value,\n',
    '                        zelf.index,\n',
    '                        size,\n',
    '                        offset,\n',
    '                        needs_swap,\n',
    '                        vm,\n',
    '                    )\n',
    '                }\n',
]
lines[start:end+1] = new_block
with io.open(path, 'w', encoding='utf-8', newline='') as f:
    f.writelines(lines)
print(f'descr_set patched: lines {start+1}..{end+1} replaced')
