import io, subprocess
path = 'crates/vm/src/builtins/int.rs'
with io.open(path, 'r', encoding='utf-8', newline='') as f:
    lines = f.readlines()

# 从 HEAD 恢复 add/subtract/multiply 行
orig = subprocess.run(
    ['git', 'show', 'HEAD:crates/vm/src/builtins/int.rs'],
    capture_output=True, text=True, encoding='utf-8'
).stdout
orig_lines = orig.splitlines(keepends=True)
orig_ops = {}
for l in orig_lines:
    for name in ('add:', 'subtract:', 'multiply:'):
        if l.strip().startswith(name):
            orig_ops[name.rstrip(':')] = l

for i, l in enumerate(lines):
    for name, orig_l in orig_ops.items():
        if l.strip().startswith(name + ':'):
            lines[i] = orig_l
            print('restored', name)

# 删除 fast_i64_op helper
out = []
removed = False
i = 0
while i < len(lines):
    if not removed and lines[i].strip().startswith('/// Fast path for binary int ops:'):
        # 跳过 helper:从注释到 fn 结束(找 "    }\n" 两次?简化:跳过固定行数)
        # helper 结构:5 行注释 + fn 签名到 } (17 行)
        for _ in range(27):
            i += 1
        removed = True
        continue
    out.append(lines[i])
    i += 1
assert removed, 'helper not found'
lines = out

with io.open(path, 'w', encoding='utf-8', newline='') as f:
    f.writelines(lines)
print('reverted int.rs')
