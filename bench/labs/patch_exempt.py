import io
path = 'crates/vm/src/stdlib/_ctypes/function.rs'
with io.open(path, 'r', encoding='utf-8', newline='') as f:
    lines = f.readlines()

# 在 PyCUnion 行后加 PyCFuncPtrType 豁免
target = '            || self.fast_issubclass(PyCUnion::static_type())\n'
for i, l in enumerate(lines):
    if l == target:
        lines.insert(i + 1, '            || self.class().fast_issubclass(PyCFuncPtrType::static_type())\n')
        print('exemption inserted after line', i+1)
        break
else:
    # 容错:找包含 PyCUnion 的行
    for i, l in enumerate(lines):
        if 'PyCUnion::static_type()' in l:
            lines.insert(i + 1, '            || self.class().fast_issubclass(PyCFuncPtrType::static_type())\n')
            print('exemption inserted (fuzzy) after line', i+1)
            break

with io.open(path, 'w', encoding='utf-8', newline='') as f:
    f.writelines(lines)
