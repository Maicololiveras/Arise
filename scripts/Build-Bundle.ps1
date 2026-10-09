param([Parameter(Mandatory=$true)][string]$Target, [switch]$WithTools, [string]$ReposRoot='', [string]$GentlePath='')
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$bundle=Join-Path $Target 'bundle'
New-Item -ItemType Directory -Path $bundle -Force | Out-Null
function Check-Exit([string]$step) { if($LASTEXITCODE -ne 0){throw "$step falló ($LASTEXITCODE)"} }
$nodeRoot=Join-Path $bundle 'node';New-Item -ItemType Directory -Path $nodeRoot -Force | Out-Null
Copy-Item -LiteralPath (Get-Command node).Source -Destination (Join-Path $nodeRoot 'node.exe')
# A clean installation ships Pi and Gentle Shell; existing installs remain detectable.
@{ private=$true; dependencies=@{'@earendil-works/pi-coding-agent'='0.85.1';'gentle-pi'='3.3.0'} } | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $nodeRoot 'package.json') -Encoding UTF8
& npm install --prefix $nodeRoot --ignore-scripts --no-audit --no-fund;Check-Exit 'Pi y Gentle Shell'
$gentle='@bundle/node/node_modules/gentle-pi'
if($GentlePath){
    $source=(Resolve-Path -LiteralPath $GentlePath).Path
    if(-not(Test-Path -LiteralPath (Join-Path $source 'extensions'))){throw 'GentlePath no contiene extensions'}
    $custom=Join-Path $bundle 'gentle-shell';Copy-Item -LiteralPath $source -Destination $custom -Recurse
    $gentle='@bundle/gentle-shell'
}
$manifest=@{
    pi_command=@('@bundle/node/node.exe','@bundle/node/node_modules/@earendil-works/pi-coding-agent/dist/cli.js')
    gentle_path=$gentle
    versions=@{pi='0.85.1';gentle='3.3.0';arise='0.2.0'}
    mcp=@{}
}
if($WithTools){
    if(-not $ReposRoot){throw '-WithTools requiere -ReposRoot con screenview-mcp, inputcontrol-mcp, transcripcion-ia y forge-mcp'}
    $repos=(Resolve-Path -LiteralPath $ReposRoot).Path
    foreach($name in @('screenview-mcp','inputcontrol-mcp','transcripcion-ia','forge-mcp')){
        if(-not(Test-Path -LiteralPath (Join-Path $repos $name))){throw "Falta $name"}
    }
    # Embedded Python is relocatable; pip-generated .exe launchers are deliberately avoided.
    $pythonRoot=Join-Path $bundle 'python';New-Item -ItemType Directory -Path $pythonRoot -Force | Out-Null
    $archive=Join-Path $env:TEMP ('arise-python-'+[guid]::NewGuid()+'.zip')
    Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip' -OutFile $archive
    Expand-Archive -LiteralPath $archive -DestinationPath $pythonRoot;Remove-Item -LiteralPath $archive
    @('python312.zip','.','Lib\site-packages','import site') | Set-Content -LiteralPath (Join-Path $pythonRoot 'python312._pth') -Encoding ASCII
    $site=Join-Path $pythonRoot 'Lib\site-packages'
    & python -m pip install --target $site ("{0}[windows]" -f (Join-Path $repos 'screenview-mcp')) ("{0}[windows]" -f (Join-Path $repos 'inputcontrol-mcp')) (Join-Path $repos 'transcripcion-ia')
    Check-Exit 'MCP Python'
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'mcp_entry.py') -Destination (Join-Path $bundle 'mcp_entry.py')
    foreach($row in @(@('screenview','screenview_mcp.server:main'),@('inputcontrol','inputcontrol_mcp.server:main'),@('transcripcion','transcripcion_mcp.server:main'))){
        $manifest.mcp[$row[0]]=@{command=@('@bundle/python/python.exe','@bundle/mcp_entry.py',$row[1]);enabled=$true}
    }
    $forge=Join-Path $repos 'forge-mcp'
    Push-Location $forge
    try{
        & npm ci --ignore-scripts;Check-Exit 'Dependencias Forge'
        & npm run build;Check-Exit 'Build Forge'
        $pack=& npm pack --ignore-scripts --json;Check-Exit 'Empaquetar Forge'
        $filename=($pack | ConvertFrom-Json)[0].filename
        & npm install --prefix $nodeRoot --ignore-scripts (Join-Path $forge $filename);Check-Exit 'Instalar Forge'
    }finally{Pop-Location}
    $manifest.mcp['forge']=@{command=@('@bundle/node/node.exe','@bundle/node/node_modules/forge-mcp/dist/bin/forge-mcp-cli.js');enabled=$true}
    & (Join-Path $pythonRoot 'python.exe') -c 'import screenview_mcp.server, inputcontrol_mcp.server, transcripcion_mcp.server'
    Check-Exit 'Imports reales de MCP en Python integrado'
}
$manifest | ConvertTo-Json -Depth 12 | Set-Content (Join-Path $bundle 'manifest.json') -Encoding UTF8
Write-Host "Bundle preparado en $bundle"
