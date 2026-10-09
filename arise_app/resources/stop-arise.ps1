param([Parameter(Mandatory=$true)][string]$InstallDir, [string]$DataDir = (Join-Path $env:LOCALAPPDATA 'ARISE-Orb'))
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath($InstallDir).TrimEnd('\') + '\'
function Snapshot { @(Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,ExecutablePath,CreationDate) }
function Is-Arise($process) {
    $path = $process.ExecutablePath
    $path -and $path.StartsWith($root,[StringComparison]::OrdinalIgnoreCase) -and ([IO.Path]::GetFileName($path) -in @('ARISE.exe','ARISE-host.exe'))
}
$all = Snapshot
$owned = @{}; $protected = @{}
# The helper and installer/launcher ancestors must outlive the application.
$current = $PID
while ($current) {
    $record = $all | Where-Object ProcessId -eq $current | Select-Object -First 1
    if (-not $record) { break }
    if (-not (Is-Arise $record)) { $protected[[int]$current] = $true }
    $current = $record.ParentProcessId
}
foreach($record in $all) { if(Is-Arise $record) { $owned[[int]$record.ProcessId] = $record } }
do {
    $changed = $false
    foreach($record in $all) {
        if($owned.ContainsKey([int]$record.ParentProcessId) -and -not $owned.ContainsKey([int]$record.ProcessId) -and -not $protected.ContainsKey([int]$record.ProcessId)) {
            $owned[[int]$record.ProcessId] = $record; $changed = $true
        }
    }
} while($changed)
# This also supports upgrading 0.3.0, which did not yet expose --shutdown.
$descriptor = Join-Path $DataDir 'daemon.json'
if(Test-Path -LiteralPath $descriptor) {
    try {
        $data = Get-Content -LiteralPath $descriptor -Raw | ConvertFrom-Json
        if($owned.ContainsKey([int]$data.pid) -and $data.url -match '^http://127\.0\.0\.1:\d+$') {
            Add-Type -AssemblyName System.Security
            $token = [Text.Encoding]::UTF8.GetString([Security.Cryptography.ProtectedData]::Unprotect([Convert]::FromBase64String($data.token),$null,[Security.Cryptography.DataProtectionScope]::CurrentUser))
            Invoke-RestMethod -Uri ($data.url+'/api/shutdown') -Method Post -ContentType 'application/json' -Body '{}' -Headers @{Authorization=('Bearer '+$token)} -TimeoutSec 15 | Out-Null
        }
    } catch { Write-Verbose 'Resident shutdown was unavailable; checking exact owned processes.' }
}
$engine = Join-Path $InstallDir 'ARISE.exe'
if($owned.Count -and (Test-Path -LiteralPath $engine)) {
    try { $stop = Start-Process -FilePath $engine -ArgumentList @('--shutdown','--data-dir',('"'+$DataDir+'"')) -PassThru; if(-not $stop.WaitForExit(30000)){ $stop.Kill(); $stop.WaitForExit() } } catch { Write-Verbose 'Older UI requires the bounded fallback.' }
}
# Give session persistence/voice/MCP shutdown a grace period before forced cleanup.
$deadline = [DateTime]::UtcNow.AddSeconds(15)
do {
    $live = @(Snapshot | Where-Object { $owned.ContainsKey([int]$_.ProcessId) -and $_.CreationDate -eq $owned[[int]$_.ProcessId].CreationDate })
    if(-not $live.Count) { break }; Start-Sleep -Milliseconds 200
} while([DateTime]::UtcNow -lt $deadline)
foreach($record in $live) {
    $now = Get-CimInstance Win32_Process -Filter ('ProcessId='+$record.ProcessId) -ErrorAction SilentlyContinue
    if($now -and $now.CreationDate -eq $record.CreationDate -and -not $protected.ContainsKey([int]$record.ProcessId)) { Stop-Process -Id $record.ProcessId -Force -ErrorAction Stop }
}
Start-Sleep -Milliseconds 300
$remaining = @(Snapshot | Where-Object { (Is-Arise $_) -or ($owned.ContainsKey([int]$_.ProcessId) -and $_.CreationDate -eq $owned[[int]$_.ProcessId].CreationDate) })
if($remaining.Count) { throw 'No se pudieron cerrar todos los procesos de ARISE. La instalación no continuará.' }
