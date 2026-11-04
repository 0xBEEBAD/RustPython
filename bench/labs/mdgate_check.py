"""Prove the md* descriptor gates actually reach a warmed call site.

An ablation that reads 1.00 is only a null result if the gate is on the route the
program takes, so this prints what a specialized no-argument method-descriptor
call returns: the real value normally, `None` under `mdarm`/`mdstub` for the
method named in `LUNA_STUB_MD`.

    LUNA_ABLATE=mdstub LUNA_STUB_MD=isascii python bench/labs/mdgate_check.py
"""

import os

s = "abcdefgh"
result = None
for _ in range(300):
    result = s.isascii()

print(
    "LUNA_ABLATE=%r LUNA_STUB_MD=%r warm str.isascii() -> %r"
    % (os.environ.get("LUNA_ABLATE", ""), os.environ.get("LUNA_STUB_MD", ""), result)
)
