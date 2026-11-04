import io
path = 'crates/capi/src/moduleobject.rs'
with io.open(path, 'r', encoding='utf-8', newline='') as f:
    content = f.read()
content = content.replace(
    '        if PyModuleDef_Init(def).is_null() {',
    '        if unsafe { PyModuleDef_Init(def) }.is_null() {'
)
with io.open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(content)
print('unsafe block added')
