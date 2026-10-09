param([switch]$WithTools, [string]$ReposRoot = '', [string]$GentlePath = '')
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $root
function Check-Exit([string]$step) { if ($LASTEXITCODE -ne 0) { throw "$step falló ($LASTEXITCODE)" } }
if ($env:OS -ne 'Windows_NT') { throw 'Este build necesita Windows x64.' }
& python -m pip install 'torch==2.8.0' --index-url https://download.pytorch.org/whl/cpu; Check-Exit 'Whisper CPU'
& python -m pip install '.[build,local,whisper]'; Check-Exit 'Dependencias de build'
& cargo test --locked --manifest-path host/Cargo.toml; Check-Exit 'Tests Rust'
& cargo build --release --locked --manifest-path host/Cargo.toml; Check-Exit 'Supervisor Rust'
& python -m PyInstaller --noconfirm --clean --windowed --onedir --name ARISE --collect-all faster_whisper --collect-all ctranslate2 --collect-all whisper --collect-all vosk --collect-all sounddevice --add-data 'web;web' --add-data 'assets;assets' --add-data 'arise_app/resources;arise_app/resources' run.py
Check-Exit 'Aplicación nativa'
$target = Join-Path $root 'dist\ARISE'
Copy-Item -LiteralPath 'host\target\release\arise-host.exe' -Destination (Join-Path $target 'ARISE-host.exe')
& "$PSScriptRoot\Build-Bundle.ps1" -Target $target -WithTools:$WithTools -ReposRoot $ReposRoot -GentlePath $GentlePath
Copy-Item -LiteralPath 'README.md' -Destination $target
$compiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if (-not $compiler) {
    $candidate = 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'
    if (Test-Path -LiteralPath $candidate) { $compiler = @{ Source = $candidate } }
}
if ($compiler) { & $compiler.Source "packaging\ARISE.iss"; Check-Exit 'Instalador' }
else { Write-Host 'Build portable listo. Para generar ARISE-Setup.exe instala Inno Setup 6 y compila packaging/ARISE.iss.' }
