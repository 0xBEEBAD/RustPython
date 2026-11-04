import io
path = 'crates/vm/src/stdlib/_imp.rs'
with io.open(path, 'r', encoding='utf-8', newline='') as f:
    lines = f.readlines()

# 恢复 extension_suffixes 返回空,但保留解释注释
start = None
for i, l in enumerate(lines):
    if 'fn extension_suffixes(vm: &VirtualMachine) -> Vec<PyObjectRef> {' in l:
        start = i
        break
assert start is not None
# 找函数结束
depth = 0
end = None
for i in range(start, len(lines)):
    depth += lines[i].count('{') - lines[i].count('}')
    if depth == 0 and i > start:
        end = i
        break
assert end is not None
print('replacing lines', start+1, '..', end+1)

new_block = [
    '    fn extension_suffixes() -> Vec<PyObjectRef> {\n',
    '        // Native extension modules (.pyd/.so) cannot be loaded yet\n',
    '        // (no C-extension ABI support); returning an empty list keeps\n',
    '        // extension importers from looking for them, which also lets\n',
    '        // CPython\'s extension test-suite modules skip themselves.\n',
    '        // Populate with platform suffixes once .pyd/.so loading lands.\n',
    '        Vec::new()\n',
    '    }\n',
]
lines[start:end+1] = new_block
with io.open(path, 'w', encoding='utf-8', newline='') as f:
    f.writelines(lines)
print('reverted extension_suffixes (documented)')
