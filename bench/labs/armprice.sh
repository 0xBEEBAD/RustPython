#!/usr/bin/env bash
# Price the pieces of one specialized Python call inside one binary.
#
# Each column is the same probe (callfloor.py) run under one set of measurement
# ablations, so a difference between two neighbouring columns is the cost of
# exactly the code that the second column switches off. Names are defined in
# crates/vm/src/perf_debug.rs.
#
#   usage: bench/labs/armprice.sh [exe] [probe] [outer-reps]
set -u
EXE=${1:-target/release/rustpython.exe}
PROBE=${2:-bench/labs/callfloor.py}
REPS=${3:-2}
STUB=LUNA_STUB_BODY=zzcallfloor

cfg_names=(live stub stage_ga stage noga_ne noga)
cfg_envs=(
  ""
  "$STUB"
  "$STUB LUNA_ABLATE=armstage"
  "$STUB LUNA_ABLATE=armstage,armguards"
  "$STUB LUNA_ABLATE=armguards,noenter"
  "$STUB LUNA_ABLATE=armguards"
)

declare -A best
for i in "${!cfg_names[@]}"; do
  name=${cfg_names[$i]}
  for _ in $(seq "$REPS"); do
    # shellcheck disable=SC2086  # the config strings are space-separated assignments
    out=$(env ${cfg_envs[$i]} "$EXE" "$PROBE" 2>&1 | tr -d '\r')
    while IFS= read -r line; do
      case "$line" in
        *ns/iter)
          label=${line%% *}
          ns=$(printf '%s' "$line" | awk '{print $2}')
          case "$ns" in
            *[!0-9.]*) continue ;;
          esac
          key="$name:$label"
          cur=${best[$key]:-}
          if [ -z "$cur" ] || awk -v a="$ns" -v b="$cur" 'BEGIN{exit !(a<b)}'; then
            best[$key]=$ns
          fi
          ;;
      esac
    done <<< "$out"
  done
done

labels=(empty call_0 call_2 call_add wide8 local8 closure method_cached method_attr)
printf '%-14s' "case"
for name in "${cfg_names[@]}"; do printf '%10s' "$name"; done
printf '\n'
for label in "${labels[@]}"; do
  printf '%-14s' "$label"
  for name in "${cfg_names[@]}"; do printf '%10s' "${best[$name:$label]:-?}"; done
  printf '\n'
done

cat <<'EOF'

read: live   real callee, normal route          stub  same with the body skipped
      stage_ga/stage  no frame at all, guards on/off
      noga_ne  frame built and arguments bound, not entered, guards off
      noga     frame entered, body stubbed, guards off

      guards       = stage_ga - stage
      frame+bind   = noga_ne - stage
      enter+return = noga - noga_ne
      body         = live - stub (stub also drops tail-call... same route, so it is the body)
      dispatch+stage = stage - empty
EOF
