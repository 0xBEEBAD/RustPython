import sys

sys.stdout.reconfigure(line_buffering=True)

# 1. simple text read
f = open(r"Lib\test\test_importlib\extension\test_loader.py", encoding="utf-8")
data = f.read()
print("1. text read ok:", len(data))
f.close()

# 2. simple write/read roundtrip
with open(r"bench\labs\_tmp.txt", "w", encoding="utf-8") as f:
    f.write("hello world")
with open(r"bench\labs\_tmp.txt", encoding="utf-8") as f:
    print("2. roundtrip:", repr(f.read()))

# 3. binary read
with open(r"bench\labs\_tmp.txt", "rb") as f:
    print("3. binary:", f.read())

# 4. plain open (default encoding)
with open(r"Lib\test\test_importlib\extension\test_loader.py") as f:
    print("4. default encoding read:", len(f.read()))

# 5. encoding='utf-8-sig'
with open(r"Lib\test\test_importlib\extension\test_loader.py", encoding="utf-8-sig") as f:
    print("5. utf-8-sig read:", len(f.read()))
print("DONE")
