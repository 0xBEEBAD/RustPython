import difflib, pathlib
ours = pathlib.Path("RustPython/Lib"); theirs = pathlib.Path("cpython315-src/cpython-3.15/Lib")
rows = []
for path in sorted(ours.rglob("*.py")):
    rel = path.relative_to(ours)
    parts = rel.parts
    if parts[0] == "test" or parts[:2] == ("idlelib",):
        continue
    other = theirs / rel
    if not other.exists():
        continue
    a = other.read_text(encoding="utf-8", errors="replace").splitlines()
    b = path.read_text(encoding="utf-8", errors="replace").splitlines()
    n = sum(1 for line in difflib.unified_diff(a, b, n=0) if line[:1] in "+-" and line[3:4] not in "+-")
    if n:
        markers = sum(1 for line in b if "RUSTPYTHON" in line)
        rows.append((n, str(rel), markers))
rows.sort(reverse=True)
print(f"library files still differing from 3.15: {len(rows)}")
for n, name, m in rows[:25]:
    print(f"  {n:5d}  {name}  (rustpython patches: {m})")
