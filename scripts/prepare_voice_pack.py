"""Prepare offline Vosk files and an independently installable model ZIP."""
import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from arise_app.downloads import download_wake, URL

README = '''ARISE · Modelos de voz en español

Incluye vosk-model-small-es-0.42 (Apache-2.0), de AC Technologies LLC.
Fuente: https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip

En ARISE: Ajustes > Voz y audio > Instalar ZIP de modelos de voz.
Selecciona este ZIP, guarda los ajustes y elige proveedor local.
Motor auto: reutiliza faster-whisper/Whisper existentes y usa Vosk cuando no hay otro modelo.
Motor vosk: usa el modelo del paquete para transcribir y para la activación.
La respuesta hablada usa las voces instaladas de Windows (SAPI); no necesitan un modelo separado.
Para activar por voz, marca la escucha local y configura una frase reconocible en español.

Tus modelos existentes NO se incluyen ni se convierten:
- %USERPROFILE%\\.cache\\whisper\\base.pt y small.pt: motor openai-whisper.
- D:\\Transcripcion con ia\\whisper_models\\base, medium y tiny: motor faster-whisper.
Usa Detectar mis modelos de voz o selecciona manualmente la ruta.
El instalador Windows ya incluye ambos motores, con cómputo CPU.

manifest.json contiene los hashes SHA-256 de los archivos de este paquete.
No contiene claves, sesiones, modelos de lenguaje ni archivos del usuario.
'''

def prepare(destination, output=None, source=None):
    destination = Path(destination); destination.mkdir(parents=True, exist_ok=True)
    target = destination / 'models/vosk-model-small-es-0.42'
    if source:
        source = Path(source)
        if source.resolve() != target.resolve(): shutil.copytree(source, target, dirs_exist_ok=True)
    else:
        target = Path(download_wake(destination))
    (destination / 'LEEME.txt').write_text(README, encoding='utf-8')
    shutil.copyfile(Path(__file__).resolve().parents[1] / 'arise_app/resources/VOSK-LICENSE.txt', destination / 'VOSK-LICENSE.txt')
    files = {str(p.relative_to(destination)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(target.rglob('*')) if p.is_file()}
    manifest = {'format':'arise-voice-pack-v1','model':'vosk-model-small-es-0.42','license':'Apache-2.0','source':URL,'files':files}
    (destination / 'voice-models.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    if output:
        output = Path(output); output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for p in sorted(target.rglob('*')):
                if p.is_file(): archive.write(p, str(p.relative_to(destination)).replace('\\', '/'))
            archive.write(destination / 'LEEME.txt', 'LEEME.txt')
            archive.write(destination / 'VOSK-LICENSE.txt', 'VOSK-LICENSE.txt')
            archive.write(destination / 'voice-models.json', 'manifest.json')
        print(json.dumps({'zip':str(output),'bytes':output.stat().st_size,'sha256':hashlib.sha256(output.read_bytes()).hexdigest()}))
    return target

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--destination', required=True); parser.add_argument('--output'); parser.add_argument('--source')
    args=parser.parse_args(); prepare(args.destination, args.output, args.source)
