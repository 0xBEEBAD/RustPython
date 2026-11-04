import io
path = 'crates/vm/src/stdlib/_ctypes/base.rs'
with io.open(path, 'r', encoding='utf-8', newline='') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'matches!(s.as_wtf8().as_slice()' in l:
        lines[i] = '                    matches!(s.as_wtf8().to_string_lossy().as_ref(), "b" | "h" | "i" | "l" | "q" | "n")\n'
        print('fixed line', i+1)
        break
else:
    print('NOT FOUND')
with io.open(path, 'w', encoding='utf-8', newline='') as f:
    f.writelines(lines)
