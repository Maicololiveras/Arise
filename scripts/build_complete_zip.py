"""One download: portable ARISE, model ZIP, and a one-click setup launcher."""
import argparse
import zipfile
from pathlib import Path

def build(application, models, output):
    application,models,output=map(Path,(application,models,output))
    if not (application/'ARISE.exe').is_file() or not models.is_file():
        raise RuntimeError('Build the Windows app and model pack first.')
    output.parent.mkdir(parents=True,exist_ok=True)
    temporary=output.with_suffix('.tmp')
    with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as archive:
        for file in sorted(application.rglob('*')):
            if file.is_file():archive.write(file,'ARISE/'+file.relative_to(application).as_posix())
        archive.write(models,'ARISE-Models-Windows.zip',compress_type=zipfile.ZIP_STORED)
        archive.writestr('Configurar ARISE.cmd','@echo off\r\n"%~dp0ARISE\\ARISE.exe" --shutdown\r\nstart "" "%~dp0ARISE\\ARISE.exe" --setup-pack "%~dp0ARISE-Models-Windows.zip"\r\n')
        archive.writestr('LEEME.txt','ARISE para Windows x64\n\n1. Extrae este ZIP completo en una carpeta permanente.\n2. Abre Configurar ARISE.cmd.\n3. ARISE verifica los archivos, instala modelos en tus datos locales y prueba el servidor.\n\nNo borres la carpeta ARISE: contiene la aplicacion portable. No necesita Python, Node ni LM Studio instalados. El modo local usa CPU. La primera preparacion requiere espacio para el paquete y los modelos extraidos.\n\nIncluye Vosk espanol, Whisper small, Qwen2.5-1.5B-Instruct Q4_K_M y llama.cpp Windows CPU. La voz de salida usa Windows SAPI. El microfono se activa con su boton; escuchar continuamente sigue siendo opcional.\n\nLas cuentas del agente/Gmail y los repositorios privados se conectan por separado: no se incluyen claves. La configuracion del agente Pi existente se conserva.\n')
    temporary.replace(output)
    print(str(output),output.stat().st_size,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--app',required=True);parser.add_argument('--models',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();build(args.app,args.models,args.output)
