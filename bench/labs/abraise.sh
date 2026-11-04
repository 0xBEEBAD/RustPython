#!/bin/bash
# Price the raise path one ablation at a time, printing the whole decomposition
# so each component's delta is visible: a plain call, an exception constructed but
# not raised, raise+catch in one frame, and bench.py's call+raise+catch across a
# frame boundary.
#
#   bash bench/labs/abraise.sh [exe]
EXE=${1:-target/release/rustpython.exe}
declare -A BITS=([base]=0 [excctx]=134217728 [excunwindtail]=268435456 [excargs]=536870912 [exctb]=1073741824 [excfuse]=262144 [excctor]=4096 [noenter]=1048576)
printf "%-16s %8s %10s %12s %12s\n" shape call construct same-frame across-call
for name in base excargs exctb excctx excunwindtail excfuse excctor noenter; do
  printf "%-16s " "$name"
  LUNA_ABLATE=${BITS[$name]} "$EXE" bench/labs/raisecost.py 2>&1 | awk '
    /^call_only/ {c=$2}
    /^construct_only/ {k=$2}
    /^raise_same_frame/ {s=$2}
    /^across_call/ {b=$2}
    END {printf "%8s %10s %12s %12s\n", c, k, s, b}'
done
