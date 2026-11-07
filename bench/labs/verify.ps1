# Correctness gate for optimization work: runs the CPython stdlib test modules
# that cover the interpreter internals touched by performance changes (GC
# bookkeeping, frame publication, threading, exceptions, generators).
#
# Usage: powershell -File bench/labs/verify.ps1 [-Exe target/release/rustpython.exe]
param(
    [string]$Exe = "target/release/rustpython.exe",
    [string[]]$Tests = @(
        'test_gc', 'test_frame', 'test_generators', 'test_threading',
        'test_sys', 'test_traceback', 'test_weakref', 'test_faulthandler',
        'test_exceptions', 'test_asyncio',
        # Object-model and codec work needs coverage here: the freelist and the
        # structseq/struct-time layout both passed a gate that omitted these, so
        # byte/string/dict construction and the codec argument paths are now
        # always exercised.
        'test_bytes', 'test_codecs', 'test_dict', 'test_builtin', 'test_time',
        # struct_time is a tuple whose body is longer than it shows, and `+`
        # reads that body; only this module watches the visible-field rule.
        'test_structseq'
    ),
    [int]$Jobs = 6,
    [switch]$SkipRust
)

$sw = [System.Diagnostics.Stopwatch]::StartNew()
# With -File, PowerShell passes "a,b,c" as one literal string, so split here.
$Tests = $Tests | ForEach-Object { $_ -split ',' } | Where-Object { $_ }
# A name that is not a file in Lib/test does not fail loudly: the runner reports
# it as an uncaught exception with zero tests, and the whole batch comes back
# FAILURE after burning the run. Check the names first instead.
$absent = $Tests | Where-Object {
    -not ((Test-Path "Lib/test/$_.py") -or (Test-Path "Lib/test/$_/__init__.py"))
}
if ($absent) {
    Write-Host ("verify: no such test module(s): {0}" -f ($absent -join ', '))
    Write-Host ("real names available: {0}" -f (($Tests | Where-Object { Test-Path "Lib/test/$_.py" }) -join ', '))
    exit 3
}
# Rust unit tests, run only when the tree actually differs from HEAD under
# crates/. `cargo build --bin rustpython` does NOT compile #[cfg(test)] code, so
# a broken or #[ignore]d test can sit on main through six commits and every
# Python gate still says SUCCESS - which is exactly what happened to the
# lifecycle benchmark in crates/vm/src/builtins/str.rs. AGENTS.md asks for this
# command on any Rust change; here it is part of the gate so it cannot be
# forgotten, and it costs nothing when no Rust changed. -SkipRust opts out.
if (-not $SkipRust) {
    $rustChanged = git diff --name-only HEAD -- crates/ 2>$null
    if ($LASTEXITCODE -ne 0) { $rustChanged = '' }
    if ($rustChanged) {
        Write-Host ("verify: Rust sources changed ({0} file(s)); running cargo test" -f
            (@($rustChanged).Count))
        cargo test --workspace --exclude rustpython_wasm --exclude rustpython-venvlauncher --exclude rustpython-capi --release 2>&1 | Tee-Object -Variable rust | Out-Null
        $rustCode = $LASTEXITCODE
        $rust | Select-String -Pattern '^test result|^error(\[|:)' | Select-Object -First 25 |
            ForEach-Object { $_.Line }
        if ($rustCode -ne 0) {
            $msg = 'verify: cargo test FAILED exit={0}; the Python results below do not verify this change' -f $rustCode
            Write-Host $msg
            exit 4
        }
        Write-Host 'verify: cargo test ok'
    } else {
        Write-Host 'verify: no Rust changes, cargo test skipped'
    }
}

& $Exe -m test "-j$Jobs" @Tests 2>&1 | Tee-Object -Variable out | Out-Null
$code = $LASTEXITCODE
$sw.Stop()
$out | Select-String -Pattern 'Tests result|Result:|test_\w+.*(ok|FAIL|ERROR)' |
    Select-Object -First 60 | ForEach-Object { $_.Line }
Write-Host ("verify: exit={0} elapsed={1:n1}s" -f $code, $sw.Elapsed.TotalSeconds)
exit $code
