import io
path = 'crates/capi/src/moduleobject.rs'
with io.open(path, 'r', encoding='utf-8', newline='') as f:
    content = f.read()
content = content.replace(
    '                    m_methods: &METHOD as *const PyMethodDef,',
    '                    m_methods: unsafe { &METHOD as *const PyMethodDef },'
)
with io.open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(content)
print('unsafe ref fixed')
