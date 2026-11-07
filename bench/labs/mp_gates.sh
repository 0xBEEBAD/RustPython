#!/usr/bin/env bash
# Price the method-descriptor dispatch arms inside ONE binary. Every ablated
# run is paired with a control that has the SAME scope variables and NO
# LUNA_ABLATE, because an unscoped gate reads as a null result.
#
#   mdarm   - guards + stack moves only: no argument vector, no callee
#   mdstub  - adds the owned-Vec packing + FuncArgs, still no callee
#   mdctx   - callee runs, but with no call-context TLS writes (unscoped: it
#             changes nothing observable, so it needs no LUNA_STUB_MD)
#   strmethod - removes the exact-kernel shortcut, so `s.upper()` takes the same
#             Vec + FuncArgs + generic-binding route that `up(s)` always takes
#
#   usage: bash bench/labs/mp_gates.sh [probe]
set -e
cd "$(dirname "$0")/../.."
EXE="${EXE:-bench/labs/variants/rp-lite-113.exe}"
PROBE="${1:-bench/labs/mp_methodcall_price.py}"
export LUNA_STUB_STR="ZZZ"

run() { # label  stub_md  ablate
  echo "=== $1   (LUNA_STUB_MD='${2}' LUNA_ABLATE='${3}') ==="
  LUNA_STUB_MD="${2}" LUNA_ABLATE="${3}" "$EXE" "$PROBE" 2>&1 | tail -n +5
}

# upper: the exact kernel shadows the md* gates, so pair strmethod with them.
run "isascii control"     "isascii" ""
run "isascii mdarm"       "isascii" "mdarm"
run "isascii mdstub"      "isascii" "mdstub"
run "upper control"       "upper"   "strmethod"
run "upper mdarm"         "upper"   "strmethod,mdarm"
run "upper mdstub"        "upper"   "strmethod,mdstub"
run "mdctx (unscoped)"    ""        "mdctx"
run "plain"               ""        ""

# split: the kernel gates are scoped by the receiver prefix ZZZ.
for abl in "" "splbind" "splpiece" "spscan" "spnode" "splreuse" "split"; do
  echo "=== split gate LUNA_ABLATE='${abl}' ==="
  LUNA_STUB_MD="" LUNA_ABLATE="$abl" "$EXE" "$PROBE" 2>&1 | tail -n +5 | grep -E "^case|split"
done

for abl in "" "mdarm" "mdstub"; do
  echo "=== split arm LUNA_ABLATE='${abl}' LUNA_STUB_MD=split ==="
  LUNA_STUB_MD="split" LUNA_ABLATE="$abl" "$EXE" "$PROBE" 2>&1 | tail -n +5 | grep -E "^case|split"
done
