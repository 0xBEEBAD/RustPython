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
        'test_exceptions', 'test_asyncio'
    ),
    [int]$Jobs = 6
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
& $Exe -m test "-j$Jobs" @Tests 2>&1 | Tee-Object -Variable out | Out-Null
$code = $LASTEXITCODE
$sw.Stop()
$out | Select-String -Pattern 'Tests result|Result:|test_\w+.*(ok|FAIL|ERROR)' |
    Select-Object -First 60 | ForEach-Object { $_.Line }
Write-Host ("verify: exit={0} elapsed={1:n1}s" -f $code, $sw.Elapsed.TotalSeconds)
exit $code
