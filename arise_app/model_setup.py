"""Selective model downloads, verified before activating any settings."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import urllib.request
import uuid
from .model_sources import SOURCES
from .downloads import download_wake, safe_extract
from .offline_pack import LOCK

GROUPS = {
    'whisper': ['models/small.pt'],
    'piper': ['piper.zip', 'models/es_MX-ald-medium.onnx', 'models/es_MX-ald-medium.onnx.json', 'licenses/PIPER-VOICE-MODEL-CARD.txt'],
    'dialogue': ['models/dialogue.gguf', 'llama.zip'],
}


def download_file(relative, target, notify):
    url, expected = SOURCES[relative]
    target.parent.mkdir(parents=True, exist_ok=True)
    total = 0; digest = hashlib.sha256(); reported = -1
    with urllib.request.urlopen(url, timeout=90) as source, target.open('xb') as output:
        while block := source.read(1024*1024):
            total += len(block)
            if total > 2*1024**3: raise RuntimeError('El archivo supera el límite de descarga.')
            digest.update(block); output.write(block)
            progress = total // (25*1024**2)
            if progress != reported:
                reported = progress; notify(f'{Path(relative).name}: {total//1024**2} MB descargados…')
    if digest.hexdigest() != expected: raise RuntimeError('Descarga incompleta o SHA-256 incorrecto: '+relative)


def prepare_model(name, root, notify):
    if name == 'vosk':
        path = download_wake(root)
        # Wake and STT share Vosk, but installing wake must not replace Whisper.
        return {'wake_model':path}
    for relative in GROUPS[name]: download_file(relative, root/relative, notify)
    if name == 'whisper':
        import whisper
        model = whisper.load_model(str(root/'models/small.pt'), device='cpu'); del model
        return {'local_stt_engine':'openai-whisper', 'local_stt_model':str(root/'models/small.pt')}
    if name == 'piper':
        import subprocess, wave
        safe_extract(root/'piper.zip', root/'tts'); (root/'piper.zip').unlink()
        executable = root/'tts/piper/piper.exe'; model = root/'models/es_MX-ald-medium.onnx'
        output = root/'probe.wav'
        subprocess.run([str(executable), '--model', str(model), '--output_file', str(output)], input=b'Hola, soy ARISE.\n', capture_output=True, check=True, timeout=60, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        with wave.open(str(output)) as audio:
            if audio.getnchannels()!=1 or audio.getnframes()<1000: raise RuntimeError('Piper no generó audio válido.')
        output.unlink()
        return {'piper_command':[str(executable)], 'piper_model':str(model), 'local_tts':'system', 'voice':'Piper es-MX Ald'}
    safe_extract(root/'llama.zip', root/'server'); (root/'llama.zip').unlink()
    executables = list((root/'server').rglob('llama-server.exe'))
    if len(executables)!=1: raise RuntimeError('Falta el servidor del modelo conversacional.')
    with (root/'models/dialogue.gguf').open('rb') as stream:
        if stream.read(4)!=b'GGUF': raise RuntimeError('Modelo conversacional inválido.')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0)); port = sock.getsockname()[1]
    return {'local_dialogue_enabled':True, 'local_dialogue_url':f'http://127.0.0.1:{port}/v1',
            'local_dialogue_model':'arise-local', 'local_server_command':[str(executables[0]), '--model',str(root/'models/dialogue.gguf'), '--alias','arise-local','--host','127.0.0.1','--port',str(port),'--ctx-size','4096','--jinja','--n-gpu-layers','0']}


def install_models(runtime, selected):
    if not isinstance(selected,list) or not selected or any(name not in ('vosk',*GROUPS) for name in selected):
        raise ValueError('Selección de modelos inválida.')
    if os.name != 'nt': raise RuntimeError('Los modelos configurables requieren Windows x64.')
    if not LOCK.acquire(blocking=False): raise RuntimeError('Ya hay una instalación de modelos en curso.')
    try:
        with runtime.transition_lock:
            if runtime.busy: raise RuntimeError('Detén la tarea activa antes de instalar modelos.')
            if getattr(runtime,'voice_service',None): runtime.voice_service.end_session()
            return _install(runtime, list(dict.fromkeys(selected)))
    finally: LOCK.release()


def _install(runtime, selected):
    root = runtime.storage.root/'models'/('download-'+uuid.uuid4().hex); root.mkdir(parents=True)
    previous = json.loads(json.dumps(runtime.storage.config)); changed = False
    try:
        settings = {}
        for name in selected:
            runtime.emit('notice', {'text':'Descargando y verificando '+name+'…'})
            settings.update(prepare_model(name, root/name, lambda text:runtime.emit('notice',{'text':text})))
        changed = True
        runtime.settings(settings)
        if 'dialogue' in selected:
            from .local_dialogue import LocalDialogue
            dialogue = LocalDialogue(runtime)
            result = dialogue.request('chat/completions', {'model':dialogue.model, 'messages':[{'role':'user','content':'Responde: Listo.'}], 'max_tokens':16}, timeout=90)
            if not result.get('choices',[{}])[0].get('message',{}).get('content'): raise RuntimeError('El modelo local no respondió a la prueba.')
            runtime.model_service.close()
        return {'installed':selected, 'configured':list(settings)}
    except Exception:
        if changed:
            runtime.model_service.close(); runtime.settings(previous)
        shutil.rmtree(root, ignore_errors=True)
        raise
