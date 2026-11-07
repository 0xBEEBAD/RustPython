#!/bin/bash
# Noise floor: interleave the unablated control with the bits that read slower
# than it, so a "+50 ns" verdict can be told apart from run-to-run spread.
#   bash bench/labs/rp_exc_noise.sh
EXE=${1:-bench/labs/variants/rp-lite-119.exe}
declare -A N=( [base]=0 [exctb]=1073741824 [excchain]=70368744177664 [excgcqueue]=1125899906842624 )
for rep in 1 2 3; do
  for name in base exctb excchain excgcqueue; do
    LUNA_ABLATE=${N[$name]} "$EXE" bench/labs/rp_exc_chain.py 2>&1 | awk -v n="$name" -v r="$rep" \
      '/^across_call\(bench\)/{printf "rep%s %-12s %10s ns\n", r, n, $2}'
  done
done
