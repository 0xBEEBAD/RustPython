# RustPython vs CPython comparison runner.
#
# Pins every run to one CPU, raises priority, alternates the two interpreters
# round-robin (so background load hits both sides equally) and keeps the best
# observation per case. Prints per-case ratios plus a geomean summary.
#
# Usage:
#   powershell -File bench/labs/cmp.ps1 -Rp target/release/rustpython.exe `
#       -Cp bench/labs/cp314/python.exe -Script bench/bench.py -Mode ops -Rounds 3
#   powershell -File bench/labs/cmp.ps1 ... -Script bench/labs/callprobe.py -Mode ns
param(
    [Parameter(Mandatory = $true)][string]$Rp,
    [Parameter(Mandatory = $true)][string]$Cp,
    [Parameter(Mandatory = $true)][string]$Script,
    [ValidateSet('ns', 'ops')][string]$Mode = 'ns',
    [int]$Rounds = 3,
    [int]$CpuMask = 1
)

function Invoke-Pinned([string]$exe, [string]$script, [int]$mask) {
    $outFile = [System.IO.Path]::GetTempFileName()
    $errFile = [System.IO.Path]::GetTempFileName()
    $p = Start-Process -FilePath $exe -ArgumentList $script `
        -NoNewWindow -PassThru -RedirectStandardOutput $outFile -RedirectStandardError $errFile
    try { $p.ProcessorAffinity = [IntPtr]$mask } catch { }
    try { $p.PriorityClass = 'High' } catch { }
    $p.WaitForExit()
    $text = (Get-Content $outFile -Raw) + "`n" + (Get-Content $errFile -Raw)
    Remove-Item $outFile, $errFile -Force -ErrorAction SilentlyContinue
    $parsed = [ordered]@{}
    foreach ($line in ($text -split "`n")) {
        if ($Mode -eq 'ns' -and $line -match '^(.+?)\s+([0-9]+\.[0-9]+)\s+ns\b') {
            $parsed[$matches[1].Trim()] = [double]$matches[2]
        }
        elseif ($Mode -eq 'ops' -and $line -match '^(.+?)\s+([0-9][0-9,]*)\s+ops/s') {
            $parsed[$matches[1].Trim()] = [double]($matches[2] -replace ',', '')
        }
    }
    return $parsed
}

$bestRp = @{}
$bestCp = @{}
for ($r = 1; $r -le $Rounds; $r++) {
    $rr = Invoke-Pinned $Rp $Script $CpuMask
    $rc = Invoke-Pinned $Cp $Script $CpuMask
    foreach ($k in $rr.Keys) {
        if (-not $bestRp.ContainsKey($k)) { $bestRp[$k] = $rr[$k] }
        elseif ($Mode -eq 'ns' -and $rr[$k] -lt $bestRp[$k]) { $bestRp[$k] = $rr[$k] }
        elseif ($Mode -eq 'ops' -and $rr[$k] -gt $bestRp[$k]) { $bestRp[$k] = $rr[$k] }
    }
    foreach ($k in $rc.Keys) {
        if (-not $bestCp.ContainsKey($k)) { $bestCp[$k] = $rc[$k] }
        elseif ($Mode -eq 'ns' -and $rc[$k] -lt $bestCp[$k]) { $bestCp[$k] = $rc[$k] }
        elseif ($Mode -eq 'ops' -and $rc[$k] -gt $bestCp[$k]) { $bestCp[$k] = $rc[$k] }
    }
    Write-Host "round $r done"
}

Write-Host ""
$label = if ($Mode -eq 'ns') { 'rp/cp (lower=faster)' } else { 'cp/rp (higher=RP faster)' }
Write-Host ("{0,-24} {1,12} {2,12} {3,10}" -f 'case', 'RustPython', 'CPython', $label)
Write-Host ("{0,-24} {1,12} {2,12} {3,10}" -f '----', '----------', '-------', '-----')
$logsum = 0.0
$n = 0
foreach ($k in $bestRp.Keys) {
    if (-not $bestCp.ContainsKey($k)) { continue }
    $rp = $bestRp[$k]; $cp = $bestCp[$k]
    $ratio = if ($Mode -eq 'ns') { $rp / $cp } else { $cp / $rp }
    Write-Host ("{0,-24} {1,12:F1} {2,12:F1} {3,10:F3}" -f $k, $rp, $cp, $ratio)
    $logsum += [Math]::Log($ratio); $n++
}
if ($n -gt 0) {
    $geo = [Math]::Exp($logsum / $n)
    Write-Host ""
    Write-Host ("geomean = {0:F3}   ({1} cases)" -f $geo, $n)
}
