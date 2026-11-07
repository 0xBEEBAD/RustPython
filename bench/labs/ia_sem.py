class Idx:
    def __index__(self): return 1
class Sub(int): pass
s = "a_b_c_d"
for label, thunk in [
  ("split(Idx())", lambda: s.split("_", Idx())),
  ("split(True)", lambda: s.split("_", True)),
  ("split(Sub(1))", lambda: s.split("_", Sub(1))),
  ("split(1.0)", lambda: s.split("_", 1.0)),
  ("split(-1)", lambda: s.split("_", -1)),
  ("split(2**70)", lambda: s.split("_", 2**70)),
  ("split(2**63)", lambda: s.split("_", 2**63)),
  ("split(2**63-1)", lambda: s.split("_", 2**63-1)),
  ("startswith(Idx())", lambda: s.startswith("b", Idx())),
  ("startswith(1.0)", lambda: s.startswith("b", 1.0)),
  ("startswith(True)", lambda: s.startswith("b", True)),
  ("startswith(2**70)", lambda: s.startswith("b", 2**70)),
  ("startswith(2**63)", lambda: s.startswith("b", 2**63)),
  ("startswith(-1)", lambda: s.startswith("a", -1)),
  ("startswith(Sub(1))", lambda: s.startswith("b", Sub(1))),
  ("find(2**70)", lambda: s.find("b", 2**70)),
  ("replace(Idx())", lambda: s.replace("_", "-", Idx())),
  ("split(maxsplit=2**63)", lambda: s.split("_", 2**63)),
]:
    try:
        print("%-22s -> %r" % (label, thunk()))
    except Exception as e:
        print("%-22s -> %s: %s" % (label, type(e).__name__, e))
