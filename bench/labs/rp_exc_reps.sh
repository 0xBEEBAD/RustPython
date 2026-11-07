#!/bin/bash
# Repeated-interleaved ablation census for the raise chain: every condition runs
# once per round, three rounds, so a delta has to survive the +-5 ns base spread
# to count. One row per (round, bit) with the four decomposition shapes.
#   bash bench/labs/rp_exc_reps.sh
EXE=${1:-bench/labs/variants/rp-lite-119.exe}
declare -A N=(
  [base]=0 [exctb]=1073741824 [excargs]=536870912 [excgctrack]=281474976710656
  [excunwindtail]=268435456 [excfuse]=262144 [exctbsnap]=35184372088832
  [excold]=140737488355328 [excsyncflot]=562949953421312 [excctx]=134217728
  [exctb_excargs]=1610612736 [exctb_excgctrack]=281476050452480
)
ORDER=(base excargs exctbsnap excold excsyncflot excgctrack excunwindtail excctx excfuse exctb exctb_excargs exctb_excgctrack)
for rep in 1 2 3; do
  for name in "${ORDER[@]}"; do
    printf "rep%s %-16s " "$rep" "$name"
    LUNA_ABLATE=${N[$name]} "$EXE" bench/labs/rp_exc_chain.py 2>&1 | awk '
      /^across_call\(bench\)/ {a=$2} /^same_frame/ {s=$2} /^call_only/ {c=$2} /^construct_only/ {k=$2}
      END {printf "across=%8s same=%8s call=%7s ctor=%7s\n", a, s, c, k}'
  done
done
