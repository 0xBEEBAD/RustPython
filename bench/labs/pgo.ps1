# Profile-guided optimization pipeline for rustpython.exe.
#
# Usage (from RustPython/):
#   powershell -File bench/labs/pgo.ps1 generate   # instrumented build (11 min)
#   powershell -File bench/labs/pgo.ps1 profile    # run the workload (~4 min)
#   powershell -File bench/labs/pgo.ps1 merge      # llvm-profdata merge (1 min)
#   powershell -File bench/labs/pgo.ps1 use        # PGO rebuild (11 min)
#
# Result: target/release/rustpython.exe built with the merged profile.
# Measured on 2026-10-29: bench.py geomean vs CPython 3.14.7 2.94x -> 2.24x,
# loop floor -22% (floorprobe.py). Re-profile if the hot code moves a lot.
param(
    [Parameter(Position = 0)]
    [ValidateSet('generate', 'profile', 'merge', 'use', 'all')]
    [string]$Stage = 'all'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)  # RustPython/
Set-Location $root
$profrawDir = 'C:/Projects/luna-lang/temp/pgo-raw'
$profdata   = 'C:/Projects/luna-lang/temp/pgo-merged.profdata'
$llvmProfdata = (Get-ChildItem "$env:USERPROFILE/.rustup/toolchains/*/lib/rustlib/x86_64-pc-windows-msvc/bin/llvm-profdata.exe" | Select-Object -First 1).FullName

# RUSTFLAGS REPLACES the rustflags from .cargo/config.toml (which carry the
# 8 MB main-thread stack reserve). Without repeating them here the PGO binary
# gets the 1 MB default and deep Python recursion raises RecursionError at
# ~200 nested calls (caught by bench/labs/test_recursion_depth.py).
$linkFlags = "-C link-arg=/STACK:8000000"

function Invoke-Cargo([string]$log) {
    # Redirect inside cmd so cargo's stderr warnings never surface as
    # PowerShell NativeCommandError under $ErrorActionPreference='Stop'.
    cmd /c "cargo build --offline --release > `"$log`" 2>&1"
    if ($LASTEXITCODE) { Get-Content $log -Tail 20; throw "cargo build failed" }
}

function Do-Generate {
    $env:RUSTFLAGS = "-Cprofile-generate=$profrawDir $linkFlags"
    Invoke-Cargo 'C:/Projects/luna-lang/temp/pgo_generate.log'
    # Instrumented binary must be copied out: the profiling workload runs it,
    # and the directory must be clean before profiling.
    New-Item -ItemType Directory -Force -Path $profrawDir | Out-Null
    Get-ChildItem $profrawDir -Filter *.profraw | Remove-Item
    Copy-Item target/release/rustpython.exe "$profrawDir/rustpython-instr.exe" -Force
}

function Do-Profile {
    $env:LLVM_PROFILE_FILE = "$profrawDir/run-%p.profraw"
    $exe = "$profrawDir/rustpython-instr.exe"
    & $exe bench/bench.py                                    | Out-Null
    & $exe bench/labs/strprobe.py                            | Out-Null
    & $exe bench/labs/floorprobe.py                          | Out-Null
    & $exe bench/labs/allocprobe.py                          | Out-Null
    # test_asyncio is deliberately absent: it hangs under parallel -m test runs.
    cmd /c "`"$exe`" -m test -j4 test_str test_dict test_list test_gc test_class test_json test_re test_enum test_generators test_exceptions > `"$profrawDir/tests.log`" 2>&1"
    if ($LASTEXITCODE) { Get-Content "$profrawDir/tests.log" -Tail 20; throw "profiling stdlib run failed" }
    (Get-ChildItem $profrawDir -Filter *.profraw).Count
}

function Do-Merge {
    & $llvmProfdata merge -o $profdata (Get-ChildItem $profrawDir -Filter *.profraw).FullName
    if ($LASTEXITCODE) { throw "llvm-profdata merge failed" }
}

function Do-Use {
    $env:RUSTFLAGS = "-Cprofile-use=$profdata -Cllvm-args=-pgo-warn-missing-function=false $linkFlags"
    Invoke-Cargo 'C:/Projects/luna-lang/temp/pgo_use.log'
}

switch ($Stage) {
    'generate' { Do-Generate }
    'profile'  { Do-Profile }
    'merge'    { Do-Merge }
    'use'      { Do-Use }
    'all'      { Do-Generate; Do-Profile; Do-Merge; Do-Use }
}
