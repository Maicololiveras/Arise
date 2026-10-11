param(
    [ValidateSet('forge','screenview','inputcontrol','all')][string]$Tool = 'all',
    [string]$Destination = "$env:LOCALAPPDATA\Programs\AriseTools"
)
$ErrorActionPreference = 'Stop'
if (-not [Environment]::Is64BitOperatingSystem -or $env:OS -ne 'Windows_NT') { throw 'Requiere Windows x64.' }
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Add-Type -AssemblyName System.IO.Compression.FileSystem
$names = @{ forge='forge-mcp'; screenview='screenview-mcp'; inputcontrol='inputcontrol-mcp' }
$selected = @($Tool); if ($Tool -eq 'all') { $selected = @('forge','screenview','inputcontrol') }
$Destination = [IO.Path]::GetFullPath($Destination)
New-Item -ItemType Directory -Force -Path $Destination | Out-Null
$configPath = Join-Path $Destination 'mcp.json'
$config = @{mcpServers=@{}}
if (Test-Path -LiteralPath $configPath) {
    $previous = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
    foreach ($property in $previous.mcpServers.PSObject.Properties) { $config.mcpServers[$property.Name] = $property.Value }
}
foreach ($item in $selected) {
    $manifest = Invoke-RestMethod -Uri "https://raw.githubusercontent.com/Maicololiveras/Arise/herramientas/manifests/$item.json"
    if ($manifest.status -eq 'pending') { throw "$item todavía no tiene un paquete publicado. Consulta README.md: configuración de publicación." }
    $name = $names[$item]
    if ($manifest.schema -ne 1 -or $manifest.tool -ne $item -or $manifest.platform -ne 'windows-x64' -or
        $manifest.sha256 -cnotmatch '^[a-f0-9]{64}$' -or $manifest.tag -cnotmatch "^herramientas-$item-v[0-9]+\.[0-9]+\.[0-9]+-[a-f0-9]{12}$" -or
        $manifest.entry -cne "$name.exe" -or $manifest.size -le 0 -or $manifest.size -gt 1073741824) { throw 'Manifiesto inválido.' }
    $expected = "https://github.com/Maicololiveras/Arise/releases/download/$($manifest.tag)/$name-windows-x64.zip"
    if ($manifest.url -cne $expected) { throw 'Origen de descarga no autorizado.' }
    $target = Join-Path $Destination $manifest.tag
    if (-not (Test-Path -LiteralPath $target)) {
        $temporary = Join-Path $Destination ('.download-' + [guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Path $temporary | Out-Null
        try {
            $zipPath = Join-Path $temporary 'package.zip'
            Write-Host "Descargando $item $($manifest.version)..."
            Invoke-WebRequest -UseBasicParsing -Uri $expected -OutFile $zipPath
            if ((Get-Item -LiteralPath $zipPath).Length -ne $manifest.size -or
                (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $manifest.sha256) { throw 'Descarga incompleta o SHA-256 incorrecto.' }
            $unpack = Join-Path $temporary 'unpack'
            $archive = [IO.Compression.ZipFile]::OpenRead($zipPath)
            try {
                $total = 0L; $seen = @{}
                foreach ($entry in $archive.Entries) {
                    $path = $entry.FullName.Replace('\','/')
                    $parts = $path.Split('/')
                    if ($path.StartsWith('/') -or $path.Contains(':') -or $parts -contains '..' -or $parts -contains '.' -or
                        $path -match '[<>"|?*]' -or $path -match '(^|/)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\.|/|$)' -or
                        $path -match '[ .](/|$)' -or $seen.ContainsKey($path) -or
                        (($entry.ExternalAttributes -shr 16) -band 0xF000) -eq 0xA000) { throw 'Ruta ZIP inválida.' }
                    $seen[$path] = $true
                    $total += $entry.Length
                    if ($total -gt 2147483648) { throw 'Paquete demasiado grande.' }
                }
            } finally { $archive.Dispose() }
            [IO.Compression.ZipFile]::ExtractToDirectory($zipPath, $unpack)
            if (-not (Test-Path -LiteralPath (Join-Path $unpack "$name.exe") -PathType Leaf)) { throw 'Falta el ejecutable.' }
            $manifest | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $unpack 'installed.json') -Encoding UTF8
            Move-Item -LiteralPath $unpack -Destination $target
        } finally { Remove-Item -LiteralPath $temporary -Recurse -Force }
    } else {
        $record = Get-Content -LiteralPath (Join-Path $target 'installed.json') -Raw | ConvertFrom-Json
        if ($record.sha256 -cne $manifest.sha256 -or -not (Test-Path -LiteralPath (Join-Path $target "$name.exe"))) { throw 'Instalación previa incompleta. Elimina solo esa versión y reintenta.' }
    }
    $config.mcpServers[$name] = @{command=(Join-Path $target "$name.exe");args=@()}
    $config | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $configPath -Encoding UTF8
    Write-Host "$item instalado: $target"
}
Write-Host "Configuración MCP generada: $configPath"
Write-Host 'Importa esos comandos en tu cliente MCP. No se modificó su configuración existente.'
