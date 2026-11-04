import io
path = 'crates/capi/src/moduleobject.rs'
with io.open(path, 'r', encoding='utf-8', newline='') as f:
    lines = f.readlines()

# 修正方法添加逻辑:用 md.ml_name 作为 dict key
old = '''            for md in methods {
                let method = build_method_def(vm, md, false)?;
                dict.set_item(
                    rustpython_vm::identifier!(vm, __name__) /* placeholder */,
                    method.into(),
                    vm,
                )
                .map_err(|e| vm.new_system_error(format!("cannot add method: {e}")))?;
            }'''
new = '''            for md in methods {
                let method = build_method_def(vm, md, false)?;
                let name = unsafe { md.ml_name.try_as_str(vm) }?;
                dict.set_item(name, method.into(), vm)
                    .map_err(|e| vm.new_system_error(format!("cannot add method: {e}")))?;
            }'''
content = ''.join(lines)
if old in content:
    content = content.replace(old, new, 1)
    with io.open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(content)
    print('method-add logic fixed')
else:
    print('pattern not found (maybe already applied)')
