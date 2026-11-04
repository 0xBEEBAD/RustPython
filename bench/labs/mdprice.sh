#!/usr/bin/env bash
# Price the specialized method-descriptor call arm inside one binary.
#
#   mdarm   - answer None without building the argument vector -> guards + moves + dispatch
#   mdstub  - build the vector and FuncArgs, skip the callee   -> adds the packing cost
#   mdctx   - run the callee with no call context              -> adds the TLS cost
#
# The callee's own cost is (default - mdstub), the packing cost is (mdstub - mdarm).
# LUNA_STUB_MD names which methods the stubs may touch, so the interpreter can
# still boot.
set -e
cd "$(dirname "$0")/../.."
EXE=target/release/rustpython.exe
PROBE="${PROBE:-bench/labs/methodprobe.py}"
export LUNA_STUB_MD="${LUNA_STUB_MD:-isascii,count,split,strip,format_map}"

for abl in mdarm mdstub mdctx; do
  echo "--- LUNA_ABLATE=$abl  (A) vs unset (B), probe=$PROBE ---"
  powershell -NoProfile -File bench/labs/ab.ps1 -A "$EXE" -B "$EXE" \
    -Script "$PROBE" -EnvA "$abl" -Rounds 5 -Mode ns
done
