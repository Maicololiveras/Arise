$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$root = Join-Path $env:TEMP ('tools-installer-test-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $root | Out-Null
$script:fixture = Join-Path $root 'fixture.zip'
$script:manifest = $null
function Invoke-RestMethod { param($Uri) return $script:manifest }
function Invoke-WebRequest { param($Uri, $OutFile, [switch]$UseBasicParsing) Copy-Item -LiteralPath $script:fixture -Destination $OutFile }
function Fixture([string]$Entry) {
    if (Test-Path $script:fixture) { Remove-Item $script:fixture }
    $z = [IO.Compression.ZipFile]::Open($script:fixture, 'Create')
    try { $e=$z.CreateEntry($Entry); $w=New-Object IO.StreamWriter($e.Open()); $w.Write('fixture'); $w.Dispose() } finally { $z.Dispose() }
    $script:manifest = [pscustomobject]@{schema=1;tool='forge';platform='windows-x64';version='0.1.0';tag='herramientas-forge-v0.1.0-aaaaaaaaaaaa';entry='forge-mcp.exe';size=(Get-Item $script:fixture).Length;sha256=(Get-FileHash $script:fixture).Hash.ToLowerInvariant();url='https://github.com/Maicololiveras/Arise/releases/download/herramientas-forge-v0.1.0-aaaaaaaaaaaa/forge-mcp-windows-x64.zip'}
}
function Expect-Failure([string]$Name) {
    $failed=$false
    try { & "$PSScriptRoot/../install.ps1" -Tool forge -Destination (Join-Path $root $Name) } catch { $failed=$true }
    if (-not $failed) { throw "$Name should have failed" }
}
try {
    Fixture 'forge-mcp.exe'
    $destination=Join-Path $root 'installed'
    & "$PSScriptRoot/../install.ps1" -Tool forge -Destination $destination
    & "$PSScriptRoot/../install.ps1" -Tool forge -Destination $destination
    $c=Get-Content (Join-Path $destination 'mcp.json') -Raw | ConvertFrom-Json
    if (-not (Test-Path -LiteralPath $c.mcpServers.'forge-mcp'.command)) { throw 'Missing installed MCP command' }
    $script:manifest.sha256='0'*64
    Expect-Failure 'checksum'
    Fixture '../escaped.exe'
    Expect-Failure 'traversal'
    Fixture 'forge-mcp.exe'
    $script:manifest.url='https://example.com/untrusted.zip'
    Expect-Failure 'origin'
    $script:manifest=[pscustomobject]@{status='pending'}
    Expect-Failure 'pending'
    Write-Host 'Installer: successful install, retry, hash failure, traversal, origin and pending checks passed.'
} finally { Remove-Item -LiteralPath $root -Recurse -Force }
