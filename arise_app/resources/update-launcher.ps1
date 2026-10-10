param([Parameter(Mandatory=$true)][string]$Plan)
$ErrorActionPreference='Stop'
try {
    $data=Get-Content -LiteralPath $Plan -Raw | ConvertFrom-Json
    if((Get-FileHash -LiteralPath $data.installer -Algorithm SHA256).Hash.ToLowerInvariant() -ne $data.sha256) { throw 'El instalador cambió después de descargarlo.' }
    & (Join-Path $PSScriptRoot 'stop-arise.ps1') -InstallDir $data.install_dir -DataDir $data.data_dir
    $arguments=@('/SP-','/NORESTART',('/DIR="'+$data.install_dir+'"'),('/ARISE-DATA="'+$data.data_dir+'"'))
    $setup=Start-Process -FilePath $data.installer -ArgumentList $arguments -PassThru -Wait
    if($setup.ExitCode -ne 0) { throw ('La instalación terminó con código '+$setup.ExitCode+'. Puedes volver a abrir la versión anterior.') }
    # Run section reopens the application only after a successful installation.
    @{status='installed';exit_code=$setup.ExitCode} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'result.json')
} catch {
    $_.Exception.Message | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'error.txt')
    $shell=New-Object -ComObject WScript.Shell
    $shell.Popup(('No se pudo actualizar ARISE: '+$_.Exception.Message),0,'ARISE Assistant',16) | Out-Null
    exit 1
}
