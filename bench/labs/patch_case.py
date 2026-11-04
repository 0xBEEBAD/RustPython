import io
path = 'crates/vm/src/builtins/str.rs'
with io.open(path, 'r', encoding='utf-8', newline='') as f:
    lines = f.readlines()

def replace_method(name, new_block):
    start = None
    for i, l in enumerate(lines):
        if f'fn {name}(zelf: PyRef<Self>)' in l:
            start = i
            break
    assert start is not None, f'{name} not found'
    s = start - 1
    depth = 0
    end = None
    for i in range(start, len(lines)):
        depth += lines[i].count('{') - lines[i].count('}')
        if depth == 0 and i > start:
            end = i
            break
    assert end is not None
    print(f'replacing {name}: lines {s+1}..{end+1}')
    lines[s:end+1] = new_block

new_lower = [
    '    #[pymethod]\n',
    '    fn lower(zelf: PyRef<Self>, vm: &VirtualMachine) -> PyRef<Self> {\n',
    '        match zelf.as_str_kind() {\n',
    '            PyKindStr::Ascii(s) => {\n',
    '                // Fast path: no ASCII uppercase letters means the result\n',
    '                // equals the input; CPython returns the same object here.\n',
    '                if !s.as_bytes().iter().any(u8::is_ascii_uppercase) {\n',
    '                    return zelf;\n',
    '                }\n',
    '                vm.ctx.new_str(s.to_ascii_lowercase())\n',
    '            }\n',
    '            PyKindStr::Utf8(s) => {\n',
    '                // Full-character check: non-ASCII characters can change\n',
    '                // case too (e.g. U+0130 LATIN CAPITAL I WITH DOT ABOVE).\n',
    '                if utf8_case_unchanged(s, char::to_lowercase) {\n',
    '                    return zelf;\n',
    '                }\n',
    '                vm.ctx.new_str(s.to_lowercase())\n',
    '            }\n',
    '            PyKindStr::Wtf8(w) => vm.ctx.new_str(w.to_lowercase()),\n',
    '        }\n',
    '    }\n',
]
new_upper = [
    '    #[pymethod]\n',
    '    fn upper(zelf: PyRef<Self>, vm: &VirtualMachine) -> PyRef<Self> {\n',
    '        match zelf.as_str_kind() {\n',
    '            PyKindStr::Ascii(s) => {\n',
    '                // Fast path: no ASCII lowercase letters means the result\n',
    '                // equals the input; CPython returns the same object here.\n',
    '                if !s.as_bytes().iter().any(u8::is_ascii_lowercase) {\n',
    '                    return zelf;\n',
    '                }\n',
    '                vm.ctx.new_str(s.to_ascii_uppercase())\n',
    '            }\n',
    '            PyKindStr::Utf8(s) => {\n',
    '                if utf8_case_unchanged(s, char::to_uppercase) {\n',
    '                    return zelf;\n',
    '                }\n',
    '                vm.ctx.new_str(s.to_uppercase())\n',
    '            }\n',
    '            PyKindStr::Wtf8(w) => vm.ctx.new_str(w.to_uppercase()),\n',
    '        }\n',
    '    }\n',
]
replace_method('lower', new_lower)
replace_method('upper', new_upper)
with io.open(path, 'w', encoding='utf-8', newline='') as f:
    f.writelines(lines)
print('done')
