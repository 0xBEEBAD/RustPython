"""Windows select() must accept as many sockets per call as CPython does.

Measured, not assumed: the reference interpreter's rule is the COUNT of
sockets, and its cap is 512 - `Modules/selectmodule.c` redefines FD_SETSIZE to
512 for MS_WINDOWS (line 47-48) and `seq2set` compares a running index against
it (`if (index >= (unsigned int)FD_SETSIZE)`, line 185) after `FD_SET`, so 512
entries pass and the 513th raises. On MS_WINDOWS the fd *value* is explicitly
"not used for Win32" (line 175), which an earlier version of this probe got
wrong and these rows now refute by observation: sockets with handles above 512
select just fine there.

Ours (crates/stdlib/src/select.rs:85-91) caps at WinSock's own FD_SETSIZE = 64,
and `platform::FD_SET` (crates/host_env/src/select.rs:50) silently drops every
handle past the 64th, so raising the check alone would turn a clean error into
missed events.

    bench/labs/cp314/python.exe                   bench/labs/test_select_fds.py
    target/release/rustpython.exe                 bench/labs/test_select_fds.py
"""

import select
import socket
import sys

ROWS = []
windows = sys.platform.startswith("win")

# The reference interpreter's cap on this platform, read off its own behaviour.
CAP = 512 if windows else 1024


def check(name, got, want):
    ROWS.append((name, repr(got), repr(want), got == want))


def try_select(socks):
    try:
        select.select(socks, [], [], 0)
        return "ok"
    except ValueError as exc:
        return f"ValueError: {exc}"


def make_sockets(count):
    """Listening sockets, which is what an asyncio selector loop registers."""
    created = []
    for _ in range(count):
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        created.append(s)
    return created


socks = make_sockets(CAP + 1 if windows else 101)
try:
    # A handle above the old 64 still selects - so the value is not the rule.
    high = [s for s in socks if s.fileno() >= 64]
    check("some handles are >= 64", len(high) > 0, True)
    check("one high handle: select", try_select(high[:1]), "ok")

    check("100 sockets: select", try_select(socks[:100]), "ok")
    check("64 sockets: select", try_select(socks[:64]), "ok")
    check("65 sockets: select", try_select(socks[:65]), "ok")
    if windows:
        check(f"{CAP} sockets: select", try_select(socks[:CAP]), "ok")
        outcome = try_select(socks[: CAP + 1])
        check(f"{CAP + 1} sockets: refused", "ValueError" in outcome, True)
        check("refusal message", outcome if "ValueError" in outcome else "none",
              "ValueError: too many file descriptors in select()")
finally:
    for s in socks:
        s.close()

bad = [r for r in ROWS if not r[3]]
for name, got, want, ok in ROWS:
    if not ok:
        print(f"FAIL {name}: got {got} want {want}")
print(f"{len(ROWS) - len(bad)}/{len(ROWS)} rows match CPython")
sys.exit(1 if bad else 0)
