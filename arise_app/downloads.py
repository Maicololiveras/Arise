"""Optional local wake model download from the official Vosk distribution."""
import shutil
import hashlib
import json
import tempfile
import urllib.request
import zipfile
from pathlib import Path
URL='https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip'

def safe_extract(archive,destination):
    destination=Path(destination).resolve();total=0
    with zipfile.ZipFile(archive) as package:
        for item in package.infolist():
            path=(destination/item.filename).resolve()
            total+=item.file_size
            if not path.is_relative_to(destination) or total>200_000_000 or (item.external_attr>>16)&0o170000==0o120000:
                raise ValueError('Archivo de modelo inválido')
        package.extractall(destination)

def download_wake(root):
    root=Path(root)/'models';root.mkdir(parents=True,exist_ok=True)
    target=root/'vosk-model-small-es-0.42'
    if (target/'am/final.mdl').is_file():return str(target)
    with tempfile.TemporaryDirectory(dir=root) as temporary:
        archive=Path(temporary)/'wake.zip';total=0
        with urllib.request.urlopen(URL,timeout=30) as response,archive.open('wb') as output:
            while True:
                chunk=response.read(1_000_000)
                if not chunk:break
                total+=len(chunk)
                if total>100_000_000:raise RuntimeError('El modelo supera el límite de descarga')
                output.write(chunk)
        safe_extract(archive,Path(temporary)/'extracted')
        extracted=Path(temporary)/'extracted/vosk-model-small-es-0.42'
        if not (extracted/'am/final.mdl').is_file():raise RuntimeError('La descarga no contiene el modelo esperado')
        shutil.move(str(extracted),str(target))
    return str(target)


def install_voice_pack(archive, root):
    """Accept both the official Vosk zip and ARISE's models/ voice package."""
    root = Path(root) / 'models'; root.mkdir(parents=True, exist_ok=True)
    target = root / 'vosk-model-small-es-0.42'
    with tempfile.TemporaryDirectory(dir=root) as temporary:
        safe_extract(archive, temporary)
        manifest = Path(temporary) / 'manifest.json'
        if manifest.is_file():
            metadata = json.loads(manifest.read_text(encoding='utf-8'))
            if metadata.get('format') != 'arise-voice-pack-v1' or not isinstance(metadata.get('files'), dict):
                raise ValueError('El manifiesto del ZIP de voz no es válido.')
            for relative, digest in metadata['files'].items():
                path = (Path(temporary) / relative).resolve()
                if not path.is_relative_to(Path(temporary).resolve()) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                    raise ValueError('El ZIP de voz está incompleto o no coincide con su manifiesto.')
        extracted = Path(temporary) / 'models/vosk-model-small-es-0.42'
        if not extracted.is_dir(): extracted = Path(temporary) / 'vosk-model-small-es-0.42'
        from .models import is_vosk
        if not is_vosk(extracted): raise ValueError('El ZIP no contiene un modelo Vosk español válido.')
        if not target.exists(): shutil.move(str(extracted), str(target))
        if not is_vosk(target): raise ValueError('La carpeta de modelo existente está incompleta; elige otra carpeta de datos.')
    return str(target)
