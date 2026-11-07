s="abcdefgh"
for lbl, th in [("count('z',None)", lambda: s.count("z", None)),
                ("count('z',None,None)", lambda: s.count("z", None, None)),
                ("count('z',0)", lambda: s.count("z", 0)),
                ("count('z',2**70)", lambda: s.count("z", 2**70)),
                ("find('z',None)", lambda: s.find("z", None)),
                ("startswith('abc',None)", lambda: s.startswith("abc", None)),
                ("startswith('abc',2**70)", lambda: s.startswith("abc", 2**70)),
                ("replace('q','r',-1)", lambda: s.replace("q","r",-1)),
                ("replace('q','r')", lambda: s.replace("q","r")),
                ("split('z',-1)", lambda: s.split("z",-1)),
                ("split('z')", lambda: s.split("z")),
                ("count('a',0)==count('a')", lambda: (s.count("a",0), s.count("a"))),
                ]:
    try: print("%-26s -> %r" % (lbl, th()))
    except Exception as e: print("%-26s -> %s: %s" % (lbl, type(e).__name__, e))
