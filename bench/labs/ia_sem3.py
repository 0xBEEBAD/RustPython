s="abcdefgh"
for lbl, th in [("expandtabs()", lambda: s.expandtabs()),
                ("expandtabs(8)", lambda: s.expandtabs(8)),
                ("expandtabs(2**70)", lambda: s.expandtabs(2**70)),
                ("expandtabs(True)", lambda: s.expandtabs(True)),
                ("splitlines()", lambda: s.splitlines()),
                ("splitlines(False)", lambda: s.splitlines(False)),
                ("split('z',maxsplit=-1)", lambda: s.split("z",maxsplit=-1)),
                ]:
    try: print("%-24s -> %r" % (lbl, th()))
    except Exception as e: print("%-24s -> %s: %s" % (lbl, type(e).__name__, e))
