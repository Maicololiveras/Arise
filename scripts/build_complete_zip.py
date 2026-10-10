"""One download: upgrading Windows installer and offline model pack."""
import argparse
import zipfile
from pathlib import Path

def build(application, models, output):
    application,models,output=map(Path,(application,models,output))
    installer=application.parent/'ARISE-Setup.exe'
    if not installer.is_file() or not models.is_file():
        raise RuntimeError('Build the Windows installer and model pack first.')
    output.parent.mkdir(parents=True,exist_ok=True)
    temporary=output.with_suffix('.tmp')
    with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as archive:
        archive.write(installer,'ARISE-Setup.exe',compress_type=zipfile.ZIP_STORED)
        archive.write(models,'ARISE-Models-Windows.zip',compress_type=zipfile.ZIP_STORED)
        archive.writestr('Configurar ARISE.cmd','@echo off\r\n"%~dp0ARISE-Setup.exe" "/ARISE-MODELS=%~dp0ARISE-Models-Windows.zip"\r\n')
        archive.writestr('LEEME.txt',
            'ARISE para Windows x64\n\n'
            '1. Extrae este ZIP completo.\n2. Abre Configurar ARISE.cmd y completa el instalador.\n'
            '3. Deja marcada Abrir ARISE: verificara y extraera los modelos y probara el servidor local.\n'
            '4. El instalador oficial de Gentle permite elegir estable o ultimo main. Confirma su plan.\n'
            'ARISE usara el Pi y el entorno configurados por Gentle. Esta etapa requiere Internet.\n\n'
            'El instalador actualiza ARISE en su carpeta existente, cierra sus procesos y conserva conversaciones y configuracion. '
            'Despues abre ARISE desde Inicio. Puedes borrar el ZIP tras completar la configuracion.\n\n'
            'Incluye modelos Vosk espanol, Whisper small, Qwen2.5-1.5B-Instruct Q4_K_M y llama.cpp Windows CPU. '
            'Voz neuronal Piper es-MX Ald gestionada por Forge. Con 8 GB se elige CPU y Vosk. La conversacion usa el mismo Gentle del chat; su proveedor puede ser local o remoto.\n\n'
            'Incluye GitHub CLI (gh). Para manos y ojos necesitas una sesion gh auth login con acceso a los repositorios privados, '
            'o conectar GitHub en Credenciales. ARISE descarga e instala los MCP y verifica sus catalogos. '
            'No se incluyen credenciales ni codigo privado. Los proveedores del agente y Gmail requieren sus propias cuentas.\n')
    temporary.replace(output)
    print(str(output),output.stat().st_size,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--app',required=True);parser.add_argument('--models',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();build(args.app,args.models,args.output)
