import io
path = 'crates/host_env/src/nt.rs'
with io.open(path, 'r', encoding='utf-8', newline='') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'pub fn add_dll_directory(path: &std::os::windows::ffi::WideCStr) -> io::Result<usize> {' in l:
        lines[i] = 'pub fn add_dll_directory(path: &widestring::WideCString) -> io::Result<usize> {\n'
        print('signature fixed at', i+1)
        break
with io.open(path, 'w', encoding='utf-8', newline='') as f:
    f.writelines(lines)
