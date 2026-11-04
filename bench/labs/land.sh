#!/bin/bash
# land.sh - one-command candidate landing pipeline for the perf/parity loop.
#
# Usage:  bash bench/labs/land.sh <tag> [ref-to-merge ...]
#   tag   short name for the resulting binary snapshot (variants/rp-pgo-<tag>.exe)
#   refs  branch names or commit SHAs, merged into main in order
#
# Why this exists: the steps (merge -> PGO-use relink -> stack check -> 5-round A/B
# -> stdlib gate) were previously hand-sequenced, and detached chains died twice,
# costing a whole measurement cycle. Run it through the harness background mode so
# it survives and notifies:
#   bash bench/labs/land.sh mytag perf/foo-1234 > temp/land-mytag.log 2>&1
set -u
cd /c/Projects/luna-lang/RustPython || exit 1
TAG=${1:?usage: land.sh <tag> [refs...]}
shift
BASE=bench/labs/variants/rp-pgo-exceptmatch.exe
NEW=bench/labs/variants/rp-pgo-$TAG.exe
GATE="test_frame,test_generators,test_exceptions,test_traceback,test_dict,test_list,test_set,test_tuple,test_str,test_bytes,test_int,test_float,test_bool,test_class,test_types,test_super,test_slice,test_range,test_iter,test_itertools,test_json,test_re,test_decimal,test_copy,test_pickle,test_struct,test_tokenize,test_keyword,test_heapq,test_codeop,test_unicodedata,test_math,test_dis,test_inspect,test_contextlib,test_contextlib_async,test_functools,test_weakref,test_sys,test_gc,test__colorize,test_hashlib,test_hmac,test_stat"

echo "=== merge refs into main: $* ==="
if [ "$#" -gt 0 ]; then
    for ref in "$@"; do
        git merge --no-ff --no-edit "$ref" >/dev/null 2>&1 || {
            echo "MERGE CONFLICT on $ref -- aborting, tree untouched"
            git merge --abort 2>/dev/null
            exit 3
        }
        echo "merged $ref -> $(git rev-parse --short HEAD)"
    done
fi
[ -s "$BASE" ] || { echo "FATAL: baseline snapshot $BASE missing"; exit 4; }

echo "=== PGO-use relink (warm cache; expect ~10 min) ==="
rm -f target/release/rustpython.exe
if ! powershell -NoProfile -File bench/labs/pgo.ps1 use > /c/Projects/luna-lang/temp/land-$TAG-cargo.log 2>&1; then
    echo "BUILD FAILED -- last 25 lines:"
    tail -25 /c/Projects/luna-lang/temp/land-$TAG-cargo.log
    exit 5
fi
SIZE=$(stat -c %s target/release/rustpython.exe 2>/dev/null || echo 0)
echo "artifact size=$SIZE"
# The instrumented binary is ~69 MB; a profiled one is ~36 MB. Anything bigger
# means the profdata was not actually applied.
if [ "$SIZE" -gt 50000000 ]; then echo "FATAL: looks instrumented, not profiled"; exit 6; fi
cp -f target/release/rustpython.exe "$NEW"

echo "=== stack reserve check ==="
python bench/labs/check_stack.py "$NEW" "$BASE" || { echo "FATAL: stack reserve regression"; exit 7; }

echo "=== A/B: baseline -> $TAG, bench.py, 5 rounds ==="
powershell -NoProfile -File bench/labs/ab.ps1 -A "$BASE" -B "$NEW" -Script bench/bench.py -Mode ops -Rounds 5 2>&1 | tail -20

echo "=== gate: 43 modules, -j6 ==="
powershell -NoProfile -File bench/labs/verify.ps1 -Exe "$NEW" -Tests "$GATE" -Jobs 6 2>&1 | tail -12

echo "=== gate: test_asyncio alone (never in a parallel batch) ==="
timeout 420 "$NEW" -m test test_asyncio 2>&1 | tail -8

echo "=== ratio vs CPython 3.14.7, 3 rounds ==="
powershell -NoProfile -File bench/labs/cmp.ps1 -Rp "$NEW" -Cp bench/labs/cp314/python.exe -Script bench/bench.py -Mode ops -Rounds 3 2>&1 | tail -18
echo "LAND DONE tag=$TAG head=$(git rev-parse --short HEAD)"
