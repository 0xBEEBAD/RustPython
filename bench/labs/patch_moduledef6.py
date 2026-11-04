import io
path = 'crates/capi/src/moduleobject.rs'
with io.open(path, 'r', encoding='utf-8', newline='') as f:
    content = f.read()
content = content.replace(
    'let rc = unsafe { f(module.as_object().as_raw().as_ptr().cast_mut()) };',
    'let rc = unsafe { f(module.as_object().as_raw().cast_mut()) };'
)
with io.open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(content)
print('as_raw fix applied')
