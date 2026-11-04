import sys

n = int(sys.argv[1]) if len(sys.argv) > 1 else 100_000
e = ValueError("boom")
for _ in range(n):
    try:
        raise e
    except ValueError:
        pass

depth = 0
cur = e.__context__
while cur is not None:
    depth += 1
    cur = cur.__context__
print("built context depth:", depth)
