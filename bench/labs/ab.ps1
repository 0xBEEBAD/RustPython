# Alternating A/B benchmark runner: pins each run to one core, raises priority,
# alternates binaries round-robin and keeps the best (min) time per case, so
# background load affects both sides equally.
#
# Usage: powershell -File bench/labs/ab.ps1 -A <exeA> -B <exeB> -Script <py> [-Rounds 4]
param(
    [Parameter(Mandatory = $true)][string]$A,
    [Parameter(Mandatory = $true)][string]$B,
    [Parameter(Mandatory = $true)][string]$Script,
    [int]$Rounds = 4,
    [int]$CpuMask = 1,
    [ValidateSet('ns','ops')][string]$Mode = 'ns',
    [string]$EnvA = '',
    [string]$EnvB = ''
)

function Invoke-Pinned([string]$exe, [string]$script, [int]$mask, [string]$envName = '') {
    $outFile = [System.IO.Path]::GetTempFileName()
    if ($env:LUNA_ABLATE) { Remove-Item Env:LUNA_ABLATE -ErrorAction SilentlyContinue }
    if ($envName) { $env:LUNA_ABLATE = $envName }
    $p = Start-Process -FilePath $exe -ArgumentList $script `
        -NoNewWindow -PassThru -RedirectStandardOutput $outFile
    try { $p.ProcessorAffinity = [IntPtr]$mask } catch { Write-Host "affinity set failed: $_" }
    try { $p.PriorityClass = 'High' } catch { }
    $p.WaitForExit()
    $text = Get-Content $outFile -Raw
    Remove-Item $outFile -Force -ErrorAction SilentlyContinue
    $parsed = @{}
    foreach ($line in ($text -split "`n")) {
        if ($Mode -eq 'ns' -and $line -match '^(.+?)\s+([0-9]+\.[0-9]+)\s+ns') {
            $parsed[$matches[1].Trim()] = [double]$matches[2]
        }
        elseif ($Mode -eq 'ops' -and $line -match '^(.+?)\s+([0-9][0-9,]*)\s+ops/s') {
            $parsed[$matches[1].Trim()] = [double]($matches[2] -replace ',', '')
        }
    }
    return $parsed
}

$bestA = @{}
$bestB = @{}
for ($r = 1; $r -le $Rounds; $r++) {
    # Alternate which binary runs first so monotonic machine drift cancels out.
    if ($r % 2 -eq 1) {
        $ra = Invoke-Pinned $A $Script $CpuMask $EnvA
        $rb = Invoke-Pinned $B $Script $CpuMask $EnvB
    } else {
        $rb = Invoke-Pinned $B $Script $CpuMask $EnvB
        $ra = Invoke-Pinned $A $Script $CpuMask $EnvA
    }
    foreach ($k in $ra.Keys) {
        if (-not $bestA.ContainsKey($k)) { $bestA[$k] = $ra[$k] }
        elseif ($Mode -eq 'ns' -and $ra[$k] -lt $bestA[$k]) { $bestA[$k] = $ra[$k] }
        elseif ($Mode -eq 'ops' -and $ra[$k] -gt $bestA[$k]) { $bestA[$k] = $ra[$k] }
    }
    foreach ($k in $rb.Keys) {
        if (-not $bestB.ContainsKey($k)) { $bestB[$k] = $rb[$k] }
        elseif ($Mode -eq 'ns' -and $rb[$k] -lt $bestB[$k]) { $bestB[$k] = $rb[$k] }
        elseif ($Mode -eq 'ops' -and $rb[$k] -gt $bestB[$k]) { $bestB[$k] = $rb[$k] }
    }
    Write-Host "round $r done"
}

Write-Host ""
# The columns hold ops/s in ops mode, so labeling them "ns" here has already
# made a 0.520 geomean read as "faster" once. Name the unit and the direction.
$unit = if ($Mode -eq 'ops') { 'ops/s' } else { 'ns' }
$reads = if ($Mode -eq 'ops') { 'B/A > 1 = B faster' } else { 'B/A < 1 = B faster' }
Write-Host ("{0,-24} {1,10} {2,10} {3,8}" -f 'case', "A $unit", "B $unit", 'B/A')
Write-Host ("{0,-24} {1,10} {2,10} {3,8}" -f '----', '----', '----', '---')
$sum = 0.0
$n = 0
foreach ($k in ($bestA.Keys | Sort-Object)) {
    if (-not $bestB.ContainsKey($k)) { continue }
    $a = $bestA[$k]; $b = $bestB[$k]
    $ratio = $b / $a
    Write-Host ("{0,-24} {1,10:F1} {2,10:F1} {3,8:F3}" -f $k, $a, $b, $ratio)
    $sum += [Math]::Log($ratio); $n++
}
if ($n -gt 0) {
    Write-Host ""
    Write-Host ("geomean B/A = {0:F3} ({1}, log-sum {2:F3}/{3})" -f [Math]::Exp($sum / $n), $reads, $sum, $n)
}
