import io
path = 'crates/vm/src/stdlib/_ctypes/array.rs'
with io.open(path, 'r', encoding='utf-8', newline='') as f:
    lines = f.readlines()
out = []
for i, l in enumerate(lines):
    if i == 593 and l.strip() == '}':
        continue  # 删除多余的闭合
    out.append(l)
with io.open(path, 'w', encoding='utf-8', newline='') as f:
    f.writelines(out)
print('removed duplicate brace at line 594')
