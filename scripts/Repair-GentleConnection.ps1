# Run with the same Windows account used to log into Gentle Shell.
$ErrorActionPreference = 'Stop'
$root = Join-Path $env:LOCALAPPDATA 'ARISE-Orb'
$settings = Join-Path $root 'settings.json'
if (!(Test-Path -LiteralPath $settings)) { throw "No existe $settings" }
$descriptor = Join-Path $root 'daemon.json'
if (Test-Path -LiteralPath $descriptor) {
    $daemon = Get-Content -LiteralPath $descriptor -Raw | ConvertFrom-Json
    if (Get-Process -Id $daemon.pid -ErrorAction SilentlyContinue) {
        throw 'Cierra ARISE con Salir (incluido el proceso residente) y ejecuta de nuevo.'
    }
}
$node = (Get-Command node.exe -ErrorAction Stop).Source
$pnpm = Get-Command pnpm.cmd -ErrorAction SilentlyContinue
if (!$pnpm) {
    $candidate = Join-Path $env:LOCALAPPDATA 'pnpm\pnpm.cmd'
    if (!(Test-Path -LiteralPath $candidate)) { throw 'No se encontro pnpm.' }
    $pnpmPath = $candidate
} else { $pnpmPath = $pnpm.Source }
# pnpm 11 validates global-bin-dir even for a read-only global listing.
# Scope the PATH adjustment to this command; do not change the user's PATH.
$previousPath = $env:Path
try {
    $pnpmBin = Join-Path $env:LOCALAPPDATA 'pnpm\bin'
    $env:Path = "$pnpmBin;$previousPath"
    $listing = & $pnpmPath list -g --depth 0 --json
    $listingExitCode = $LASTEXITCODE
} finally { $env:Path = $previousPath }
if ($listingExitCode -ne 0) { throw 'No se pudo consultar pnpm.' }
$packages = @($listing | ConvertFrom-Json)
$gentle = @($packages | ForEach-Object { $_.dependencies.'gentle-pi'.path } | Where-Object { $_ })
if ($gentle.Count -ne 1) { throw 'No se encontro una instalacion unica de Gentle.' }
$probe = Join-Path $PSScriptRoot '..\arise_app\resources\probe-gentle.mjs'
$result = & $node $probe $gentle[0]
if ($LASTEXITCODE -ne 0) { throw 'No se pudo validar el entorno de Gentle. No se modifico ARISE.' }
$found = $result | ConvertFrom-Json
$meta = Get-Content -LiteralPath (Join-Path $found.pi_root 'package.json') -Raw | ConvertFrom-Json
$cli = Join-Path $found.pi_root $meta.bin.pi
& $node $cli --version
if ($LASTEXITCODE -ne 0) { throw 'El Pi de Gentle no arranca. No se modifico ARISE.' }
$config = Get-Content -LiteralPath $settings -Raw | ConvertFrom-Json
$changes = @{
    pi_command = @($node, $cli)
    gentle_path = $found.gentle_root
    gentle_agent_home = $found.agent_home
    gentle_channel = $found.channel
    agent_provider = ''
    agent_model = ''
}
foreach ($key in $changes.Keys) { $config | Add-Member -NotePropertyName $key -NotePropertyValue $changes[$key] -Force }
$backup = "$settings.before-gentle-$([guid]::NewGuid().ToString('N')).bak"
$temp = "$settings.$([guid]::NewGuid().ToString('N')).tmp"
[IO.File]::WriteAllText($temp, ($config | ConvertTo-Json -Depth 100), (New-Object Text.UTF8Encoding($false)))
[IO.File]::Replace($temp, $settings, $backup)
Write-Host "Configuracion reparada. Copia anterior: $backup"
Write-Host "Entorno Gentle: $($found.agent_home)"
Write-Host 'Abre ARISE y crea una conversacion nueva para probar Hola.'
