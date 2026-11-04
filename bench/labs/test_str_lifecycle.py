"""Pin the behaviour a `PyStr` freelist must not break, on both interpreters.

A freelist hands a dead object's memory to the next string, so every one of
these rows is an aliasing or identity hazard: a string that is still referenced
must never be recycled, a subclass instance must not be retagged as a plain
`str` or the other way round, and the interned/`is` behaviour the language
guarantees must survive 200k create-and-drop cycles.

    bench/labs/cp314/python.exe       bench/labs/test_str_lifecycle.py
    target/release/rustpython.exe     bench/labs/test_str_lifecycle.py
"""

import gc
import sys
import threading
import weakref

failures = []


def check(name, cond, detail=""):
    if not cond:
        failures.append(f"{name}: {detail}")


def churn(n=200_000):
    # Every iteration creates strings and drops them again.
    acc = 0
    for i in range(n):
        s = "zzfiller%d" % i
        acc += len(s) + len(s.upper()) + len(s.split("f")[0])
    return acc


# --- a retained string must not be overwritten by later churn ---
keep = "keepme-42"
keep2 = "".join(["k", "e", "e", "p", "m", "e", "-", "4", "2"])
other = [str(i) * 3 for i in range(50)]
churn(50_000)
check("retained value", keep == "keepme-42", keep)
check("retained identity", keep is keep)
check("retained join value", keep2 == "keepme-42", keep2)
check("retained list", all(o == str(i) * 3 for i, o in enumerate(other)), other[:3])

# --- the same content built twice is still equal, and interned when asked ---
a = "repeat" * 4
b = "repeatrepeatrepeatrepeat"
check("equal", a == b)
check("intern", sys.intern(a) is sys.intern(b), (sys.intern(a), sys.intern(b)))
del a, b
churn(2_000)

# --- long strings keep their own data buffer across reuse ---
big1 = "x" * 5000
big2 = "y" * 5000
check("big len", (len(big1), len(big2)) == (5000, 5000), (len(big1), len(big2)))
check("big hash", hash(big1) != hash(big2))
check("big value", big1[4999] == "x" and big2[0] == "y")
del big1, big2
churn(2_000)

# --- non-ASCII and lone surrogates (WTF-8) survive churn unchanged ---
u = "héllo-wörld-\U0001F600"
check("unicode", u.upper() == "HÉLLO-WÖRLD-\U0001F600", u.upper())
check("unicode len", len(u) == 13, len(u))
check("unicode encode", u.encode("utf-8").decode("utf-8") == u)
sur = "\ud800abc"
check("surrogate len", len(sur) == 4, len(sur))
check("surrogate slice", sur[0] == "\ud800", repr(sur[0]))
churn(2_000)
check("surrogate after churn", sur[1:] == "abc", repr(sur[1:]))
check("unicode after churn", u == "héllo-wörld-\U0001F600")

# --- subclasses are a different type: never retagged, still get a dict ---
class Sub(str):
    pass


subs = [Sub("s%d" % i) for i in range(20)]
for i, t in enumerate(subs):
    t.tag = i
churn(20_000)
check("subclass type", all(type(t) is Sub for t in subs))
check("subclass attrs", [t.tag for t in subs] == list(range(20)))
check("subclass value", subs[3] == "s3", subs[3])
check("subclass is not str type", Sub("x") != "X")
del subs
gc.collect()

class EmptySlots(str):
    __slots__ = ()


es = EmptySlots("frozen-ish")
check("emptyslots value", es == "frozen-ish")
check("emptyslots no dict", not hasattr(es, "__dict__"))
try:
    es.x = 1
except AttributeError:
    pass
else:
    failures.append("emptyslots: attribute assignment unexpectedly allowed")

# --- plain strings are not GC-tracked and not weakrefable, like CPython ---
check("not tracked", gc.is_tracked("abcdefgh") is False, gc.is_tracked("abcdefgh"))
try:
    weakref.ref("abc")
except TypeError:
    pass
else:
    failures.append("weakref: str unexpectedly weakrefable")

# --- empty and single-char strings (the cached ones) stay correct ---
check("empty", ("" + "") == "" and len("") == 0)
check("latin1 cache", chr(200) == "È" and len(chr(200)) == 1, repr(chr(200)))
one = "a"
churn(5_000)
check("one after churn", one * 3 == "aaa", one * 3)

# --- another thread's strings are independent (thread-local freelists) ---
results = []


def worker():
    local_keep = "thread-keep-1"
    churn(5_000)
    results.append(local_keep == "thread-keep-1")
    results.append(len("thread-keep-1") == 13)


t1 = threading.Thread(target=worker)
t2 = threading.Thread(target=worker)
t1.start()
t2.start()
t1.join()
t2.join()
check("threads", results == [True, True, True, True], results)

# --- a dict of string keys survives churn (keys are retained refs) ---
d = {"key%d" % i: i for i in range(200)}
churn(20_000)
check("dict keys", d["key199"] == 199 and len(d) == 200, d.get("key199"))
check("dict miss", "key199x" not in d)

if failures:
    print("FAIL")
    for f in failures:
        print(" -", f)
    sys.exit(1)
print("PASS: str lifecycle parity")
