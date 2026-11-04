import io
path = 'crates/vm/src/stdlib/nt.rs'
with io.open(path, 'r', encoding='utf-8', newline='') as f:
    lines = f.readlines()

# 在 _supports_virtual_terminal 函数后加 _add_dll_directory/_remove_dll_directory
anchor = None
for i, l in enumerate(lines):
    if 'pub(super) fn _supports_virtual_terminal() -> bool {' in l:
        anchor = i
        break
assert anchor is not None
# 找该函数结束
depth = 0
end = None
for i in range(anchor, len(lines)):
    depth += lines[i].count('{') - lines[i].count('}')
    if depth == 0 and i > anchor:
        end = i
        break
assert end is not None
print('anchor ends at', end+1)

block = [
    '\n',
    '    #[pyfunction]\n',
    '    pub(super) fn _add_dll_directory(\n',
    '        path: OsPath,\n',
    '        vm: &VirtualMachine,\n',
    '    ) -> PyResult<usize> {\n',
    '        let wide = path.to_wide_cstring(vm)?;\n',
    '        host_nt::add_dll_directory(&wide)\n',
    '            .map_err(|err| vm.new_os_error(err.to_string()))\n',
    '    }\n',
    '\n',
    '    #[pyfunction]\n',
    '    pub(super) fn _remove_dll_directory(cookie: usize, vm: &VirtualMachine) -> PyResult<()> {\n',
    '        host_nt::remove_dll_directory(cookie)\n',
    '            .map_err(|err| vm.new_os_error(err.to_string()))\n',
    '    }\n',
]
lines[end+1:end+1] = block
with io.open(path, 'w', encoding='utf-8', newline='') as f:
    f.writelines(lines)
print('nt.rs pyfunctions added')
