import io
path = 'crates/capi/src/moduleobject.rs'
with io.open(path, 'r', encoding='utf-8', newline='') as f:
    content = f.read()

# 1. downcast_ref 无 vm 参数
content = content.replace(
    '                .downcast_ref::<PyModule>(vm)',
    '                .downcast_ref::<PyModule>()'
)
# 2. 错误格式化:PyBaseException 无 Display,改用异常消息提取
content = content.replace(
    '''                    .map_err(|e| vm.new_system_error(format!("cannot add method: {e}")))?;''',
    '''                    .map_err(|e| {
                        let msg = e
                            .args()
                            .first()
                            .and_then(|a| a.downcast_ref::<PyStr>().map(|s| s.to_string()))
                            .unwrap_or_else(|| "unknown error".to_string());
                        vm.new_system_error(format!("cannot add method: {msg}"))
                    })?;'''
)
# 3. module.as_raw() 的用法:module 是 PyObjectRef,用 as_object().as_raw()
content = content.replace(
    'let rc = unsafe { f(module.as_raw().as_ptr()) };',
    'let rc = unsafe { f(module.as_object().as_raw().as_ptr().cast_mut()) };'
)
with io.open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(content)
print('fixes v2 applied')
