$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
if(-not(Get-Command py -ErrorAction SilentlyContinue)){throw 'Para ejecutar desde código instala Python 3.12. El instalador compilado no lo requiere.'}
& py -3.12 -m venv .venv
if($LASTEXITCODE -ne 0){throw 'No se pudo crear el entorno'}
& .\.venv\Scripts\python.exe -m pip install .
if($LASTEXITCODE -ne 0){throw 'No se pudieron instalar las dependencias'}
& .\.venv\Scripts\python.exe run.py --settings
