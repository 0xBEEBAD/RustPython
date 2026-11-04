import io
path = 'crates/vm/src/stdlib/_ctypes/base.rs'
with io.open(path, 'r', encoding='utf-8', newline='') as f:
    lines = f.readlines()

# 定位 descr_get 中的 cdata.get_field( 调用:特征是在 "Get PyCData from obj" 之后,
# 且位于 impl GetDescriptor for PyCField 块内(第二个出现)
starts = []
for i, l in enumerate(lines):
    if 'cdata.get_field(' in l:
        starts.append(i)
print('cdata.get_field call sites:', starts)
assert len(starts) >= 1
start = starts[-1]  # descr_get 里的应该是最后一个(在文件后部)

# 找到调用结束(闭合括号行)
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

new_block = [
    '        let result = cdata.get_field(\n',
    '            zelf.proto.as_object(),\n',
    '            zelf.index,\n',
    '            size,\n',
    '            offset,\n',
    '            obj.clone(),\n',
    '            vm,\n',
    '        )?;\n',
    '        if zelf.bitfield_size > 0 {\n',
    '            // Extract the bitfield from the storage unit with unsigned\n',
    '            // semantics, matching CPython\'s b_get (cfield.c).\n',
    '            let bits = zelf.bitfield_size as u32;\n',
    '            let shift = zelf.bit_offset_val as u32;\n',
    '            let mask = (1u64 << bits) - 1;\n',
    '            let v = crate::builtins::int::get_value(&result)\n',
    '                .to_i64()\n',
    '                .ok_or_else(|| vm.new_type_error("bitfield value too large"))? as u64;\n',
    '            return Ok(vm.ctx.new_int((v >> shift) & mask).into());\n',
    '        }\n',
    '        Ok(result)\n',
]
lines[start:end+1] = new_block
with io.open(path, 'w', encoding='utf-8', newline='') as f:
    f.writelines(lines)
print(f'descr_get patched: lines {start+1}..{end+1} replaced')
