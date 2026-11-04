import io
path = 'crates/vm/src/builtins/str.rs'
with io.open(path, 'r', encoding='utf-8', newline='') as f:
    lines = f.readlines()

# 从 git 取已提交版本的 lower/upper(3fb0acb11 里的原实现),替换当前实现
import subprocess
orig = subprocess.run(
    ['git', 'show', 'HEAD:crates/vm/src/builtins/str.rs'],
    capture_output=True, text=True, encoding='utf-8'
).stdout
orig_lines = orig.splitlines(keepends=True)

# 从 orig 提取 lower 和 upper 方法(含 #[pymethod])
def extract(name):
    start = None
    for i, l in enumerate(orig_lines):
        if f'    fn {name}(&self)' in l:
            start = i - 1  # #[pymethod]
            break
    assert start is not None, f'{name} not in HEAD'
    depth = 0
    end = None
    for i in range(start + 1, len(orig_lines)):
        depth += orig_lines[i].count('{') - orig_lines[i].count('}')
        if depth == 0 and i > start + 1:
            end = i
            break
    assert end is not None
    return orig_lines[start:end+1]

def replace_current(name, new_block):
    start = None
    for i, l in enumerate(lines):
        if f'    fn {name}(zelf: PyRef<Self>' in l:
            start = i - 1
            break
    assert start is not None, f'{name} not found in current'
    depth = 0
    end = None
    for i in range(start + 1, len(lines)):
        depth += lines[i].count('{') - lines[i].count('}')
        if depth == 0 and i > start + 1:
            end = i
            break
    assert end is not None
    print(f'reverting {name}: lines {start+1}..{end+1}')
    lines[start:end+1] = new_block

replace_current('lower', extract('lower'))
replace_current('upper', extract('upper'))

# 删除 helper utf8_case_unchanged
out = []
removed = False
i = 0
while i < len(lines):
    if not removed and lines[i].startswith('/// Returns true if mapping every character'):
        for _ in range(7):
            i += 1
        removed = True
        continue
    out.append(lines[i])
    i += 1
assert removed, 'helper not found'
lines = out

with io.open(path, 'w', encoding='utf-8', newline='') as f:
    f.writelines(lines)
print('reverted to HEAD implementation')
