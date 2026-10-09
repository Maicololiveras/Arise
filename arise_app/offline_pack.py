"""Transactional, offline model installation with fixed application settings."""
import hashlib
import json
import os
import re
import shutil
import socket
import tempfile
import threading
import uuid
import zipfile
from pathlib import Path, PurePosixPath
from .models import is_vosk, VOSK_NAME

LOCK = threading.Lock()
LIMIT = 4 * 1024**3


def probe_voice(root):
    import gc
    import whisper
    import vosk
    voice = whisper.load_model(str(root/'models/small.pt'), device='cpu')
    del voice
    wake = vosk.Model(str(root/'models'/VOSK_NAME))
    del wake
    gc.collect()


def _relative(name):
    path = PurePosixPath(name)
    if (not name or path.is_absolute() or '\\' in name or ':' in name
            or any(p in ('', '.', '..') or p.endswith((' ', '.')) for p in name.split('/'))):
        raise ValueError('Ruta inválida en el paquete.')
    return path


def extract_verified(archive, destination):
    """Never load an executable or checkpoint before checking the entire archive."""
    destination = Path(destination)
    with zipfile.ZipFile(archive) as package:
        entries = package.infolist()
        if len(entries) > 10000 or len({p.filename.casefold() for p in entries}) != len(entries):
            raise ValueError('El ZIP contiene demasiados archivos o rutas duplicadas.')
        info = package.getinfo('manifest.json')
        if info.file_size > 1_000_000:
            raise ValueError('Manifiesto demasiado grande.')
        manifest = json.loads(package.read(info))
        files = manifest.get('files')
        if manifest.get('format') != 'arise-offline-pack-v1' or manifest.get('platform') != 'windows-x64' or not isinstance(files, dict):
            raise ValueError('Selecciona el ZIP completo de modelos de ARISE para Windows.')
        if set(files) != {p.filename for p in entries if p.filename != 'manifest.json'}:
            raise ValueError('El contenido no coincide con el manifiesto.')
        total = sum(p.file_size for p in entries)
        if total > LIMIT or shutil.disk_usage(destination).free < total + 512*1024**2:
            raise ValueError('El paquete es demasiado grande o no hay espacio libre suficiente.')
        for item in entries:
            _relative(item.filename)
            if item.is_dir() or (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('No se permiten enlaces ni directorios en el manifiesto.')
        for name, digest in files.items():
            if not isinstance(digest,str) or not re.fullmatch('[0-9a-f]{64}',digest):
                raise ValueError('Hash inválido en el paquete.')
            target = destination / _relative(name)
            target.parent.mkdir(parents=True,exist_ok=True)
            checksum = hashlib.sha256()
            with package.open(name) as source, target.open('xb') as output:
                while block := source.read(1024*1024):
                    checksum.update(block);output.write(block)
            if checksum.hexdigest() != digest:
                raise ValueError('El ZIP está incompleto o fue modificado: ' + name)
    server = manifest.get('server','')
    _relative(server)
    if server not in files or not server.startswith('server/') or PurePosixPath(server).name != 'llama-server.exe':
        raise ValueError('Falta el servidor de modelos del paquete.')
    if not is_vosk(destination/'models'/VOSK_NAME) or 'models/small.pt' not in files or 'models/dialogue.gguf' not in files:
        raise ValueError('Faltan modelos requeridos.')
    with (destination/server).open('rb') as stream:
        if stream.read(2) != b'MZ': raise ValueError('Servidor Windows inválido.')
    with (destination/'models/dialogue.gguf').open('rb') as stream:
        if stream.read(4) != b'GGUF': raise ValueError('Modelo conversacional inválido.')
    return manifest


def install_offline_pack(runtime, archive):
    if os.name != 'nt': raise RuntimeError('Este paquete contiene un servidor para Windows x64.')
    if not LOCK.acquire(blocking=False): raise RuntimeError('La configuración del paquete ya está en curso.')
    try:
        with runtime.transition_lock:
            if runtime.busy: raise RuntimeError('Detén la tarea activa antes de configurar los modelos.')
            if getattr(runtime,'voice_service',None): runtime.voice_service.end_session()
            return _install(runtime, archive)
    finally:
        LOCK.release()


def _install(runtime, archive):
    root = runtime.storage.root/'offline';root.mkdir(exist_ok=True)
    old = json.loads(json.dumps(runtime.storage.config))
    target = root/uuid.uuid4().hex
    changed = False
    try:
        runtime.emit('notice',{'text':'Verificando y extrayendo el paquete local de ARISE…'})
        with tempfile.TemporaryDirectory(dir=root,prefix='staging-') as temporary:
            manifest = extract_verified(archive,temporary)
            shutil.move(temporary,str(target))
        runtime.emit('notice',{'text':'Comprobando los modelos de voz…'})
        probe_voice(target)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port = sock.getsockname()[1]
        command = [str(target/manifest['server']), '--model',str(target/'models/dialogue.gguf'),
            '--alias','arise-local','--host','127.0.0.1','--port',str(port),'--ctx-size','8192','--jinja','--n-gpu-layers','0']
        runtime.settings({'onboarding_complete':True,'voice_provider':'local','local_stt_engine':'openai-whisper',
            'local_stt_model':str(target/'models/small.pt'),'wake_model':str(target/'models'/VOSK_NAME),
            'local_dialogue_enabled':True,'local_dialogue_url':f'http://127.0.0.1:{port}/v1',
            'local_dialogue_model':'arise-local','local_server_command':command})
        changed = True
        runtime.emit('notice',{'text':'Modelos instalados. Comprobando el servidor local…'})
        from .local_dialogue import LocalDialogue
        dialogue = LocalDialogue(runtime)
        # No tasks or machine tools: test actual inference without delegating work.
        result = dialogue.request('chat/completions',{'model':dialogue.model,
            'messages':[{'role':'user','content':'Responde solamente: Listo.'}], 'max_tokens':16,'temperature':0},timeout=90)
        if not result.get('choices',[{}])[0].get('message',{}).get('content'):
            raise RuntimeError('El modelo local no devolvió una respuesta de prueba.')
        runtime.emit('notice',{'text':'Configuración local completada: activación, Whisper y conversación local disponibles. Usa el botón de micrófono para hablar.'})
        return {'installed':True,'path':str(target),'model':'arise-local','inference':'passed'}
    except Exception:
        if changed:
            runtime.model_service.close()
            runtime.settings(old)
        shutil.rmtree(target,ignore_errors=True)
        raise
