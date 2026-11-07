#!/bin/bash
# Price the raise chain one ablation bit at a time on rp-lite-119, printing the
# unablated control first so every delta is read inside one binary, one profile
# and one launch batch. None of the EXC_* bits are scope-gated by LUNA_STUB_*
# (checked: frame.rs:1164/1203/1287/1435/3421/3520, vm/mod.rs:2499,
# exceptions.rs:605, gc_state.rs:340/347/362), so no scope variable is set here;
# if one ever becomes scope-gated this script must set it or the row is a silent
# no-op.
#
#   bash bench/labs/rp_exc_ablate.sh
EXE=${1:-bench/labs/variants/rp-lite-119.exe}
PROBE=bench/labs/rp_exc_chain.py
declare -A BITS=(
  [base]=0
  [exctb]=1073741824
  [excchain]=70368744177664
  [exctbsnap]=35184372088832
  [excold]=140737488355328
  [excsyncflot]=562949953421312
  [excgctrack]=281474976710656
  [excgcqueue]=1125899906842624
  [excgcnolock]=2251799813685248
  [excargs]=536870912
  [excctx]=134217728
  [excunwindtail]=268435456
  [excctor]=4096
  [excfuse]=262144
)
ORDER=(base exctb excchain exctbsnap excold excsyncflot excgctrack excgcqueue excgcnolock excargs excctx excunwindtail excctor excfuse)
printf "%-16s %10s %10s %10s %10s\n" bit across same call construct
for name in "${ORDER[@]}"; do
  bit=${BITS[$name]}
  printf "%-16s " "$name"
  LUNA_ABLATE=$bit "$EXE" "$PROBE" 2>&1 | awk '
    /^across_call\(bench\)/ {a=$2}
    /^same_frame/           {s=$2}
    /^call_only/            {c=$2}
    /^construct_only/       {k=$2}
    END {printf "%10s %10s %10s %10s\n", a, s, c, k}'
done
