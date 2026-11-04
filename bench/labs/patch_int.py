import io
path = 'crates/vm/src/builtins/int.rs'
with io.open(path, 'r', encoding='utf-8', newline='') as f:
    lines = f.readlines()

# 1. 修改 add/subtract/multiply 三行
count = 0
for i, l in enumerate(lines):
    if 'add: Some(|a, b, vm| Self::number_op(a, b, |a, b, _vm| a + b, vm)),' in l:
        lines[i] = '        add: Some(|a, b, vm| Self::fast_i64_op(a, b, i64::checked_add, |a, b, vm| (a + b).to_pyresult(vm), vm)),\n'
        count += 1
    elif 'subtract: Some(|a, b, vm| Self::number_op(a, b, |a, b, _vm| a - b, vm)),' in l:
        lines[i] = '        subtract: Some(|a, b, vm| Self::fast_i64_op(a, b, i64::checked_sub, |a, b, vm| (a - b).to_pyresult(vm), vm)),\n'
        count += 1
    elif 'multiply: Some(|a, b, vm| Self::number_op(a, b, |a, b, _vm| a * b, vm)),' in l:
        lines[i] = '        multiply: Some(|a, b, vm| Self::fast_i64_op(a, b, i64::checked_mul, |a, b, vm| (a * b).to_pyresult(vm), vm)),\n'
        count += 1
print('replaced', count, 'ops')

# 2. 在 number_op 前插入 fast_i64_op
anchor = None
for i, l in enumerate(lines):
    if 'fn number_op<F, R>' in l:
        anchor = i
        break
assert anchor is not None
helper = [
    '    /// Fast path for binary int ops: when both operands fit in i64 and\n',
    '    /// the checked operation succeeds, build the result directly without\n',
    '    /// allocating a BigInt. Falls back to the generic BigInt path\n',
    '    /// otherwise, so semantics (arbitrary precision) are unchanged.\n',
    '    fn fast_i64_op<F, B>(\n',
    '        a: &PyObject,\n',
    '        b: &PyObject,\n',
    '        op: F,\n',
    '        big_op: B,\n',
    '        vm: &VirtualMachine,\n',
    '    ) -> PyResult\n',
    '    where\n',
    '        F: Fn(i64, i64) -> Option<i64>,\n',
    '        B: FnOnce(&BigInt, &BigInt, &VirtualMachine) -> PyResult,\n',
    '    {\n',
    '        if let (Some(a), Some(b)) = (a.downcast_ref::<Self>(), b.downcast_ref::<Self>()) {\n',
    '            if let (Some(x), Some(y)) = (a.value.to_i64(), b.value.to_i64())\n',
    '                && let Some(result) = op(x, y)\n',
    '            {\n',
    '                return Ok(vm.ctx.new_int(result).into());\n',
    '            }\n',
    '            big_op(&a.value, &b.value, vm)\n',
    '        } else {\n',
    '            Ok(vm.ctx.not_implemented())\n',
    '        }\n',
    '    }\n',
    '\n',
]
lines[anchor:anchor] = helper
with io.open(path, 'w', encoding='utf-8', newline='') as f:
    f.writelines(lines)
print('fast_i64_op added')
