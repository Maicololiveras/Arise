"""Discover local model formats without downloading or converting user files."""
import importlib.util
from pathlib import Path

VOSK_NAME = "vosk-model-small-es-0.42"

def is_vosk(path):
    return (Path(path) / "am/final.mdl").is_file() and (Path(path) / "conf/model.conf").is_file()

def is_faster_whisper(path):
    return (Path(path) / "model.bin").is_file() and (Path(path) / "config.json").is_file()

def discover_voice_models(home=None, roots=None):
    home = Path(home or Path.home())
    roots = [Path(root) for root in roots] if roots is not None else [Path(r"D:\Transcripcion con ia\whisper_models"), home / ".cache/huggingface/hub"]
    found = []
    for root in roots:
        if not root.is_dir(): continue
        candidates = [root, *[root / name for name in ("base", "small", "tiny", "medium", VOSK_NAME)]]
        candidates.extend(root.glob("models--Systran--faster-whisper-*/snapshots/*"))
        for path in candidates:
            engine = "faster-whisper" if is_faster_whisper(path) else "vosk" if is_vosk(path) else None
            if engine: found.append({"engine": engine, "path": str(path.resolve()), "label": path.name})
    for name in ("base", "small", "tiny", "medium"):
        path = home / ".cache/whisper" / (name + ".pt")
        if path.is_file(): found.append({"engine": "openai-whisper", "path": str(path.resolve()), "label": name + ".pt"})
    return list({item["path"]: item for item in found}.values())

def resolve_stt(config):
    engine = config.get("local_stt_engine", "auto")
    model = config.get("local_stt_model", "").strip()
    if engine == "vosk":
        path = model if is_vosk(model) else config.get("wake_model", "")
        if not is_vosk(path): raise RuntimeError("Selecciona un modelo Vosk español válido en Ajustes.")
        return engine, str(Path(path).resolve())
    if engine == "auto":
        if model.endswith(".pt"):
            engine = "openai-whisper"
        elif is_faster_whisper(model):
            engine = "faster-whisper"
        elif is_vosk(model):
            engine = "vosk"
        elif model and (Path(model).is_absolute() or "/" in model or "\\" in model):
            raise RuntimeError("El modelo local seleccionado no existe o su formato no es compatible.")
        else:
            candidates = discover_voice_models()
            selected = next((m for m in candidates if m["engine"] == "faster-whisper"), None)
            if selected is None and importlib.util.find_spec("whisper") is not None:
                selected = next((m for m in candidates if m["engine"] == "openai-whisper"), None)
            if selected: return selected["engine"], selected["path"]
            if is_vosk(config.get("wake_model", "")): return "vosk", config["wake_model"]
            raise RuntimeError("No hay un modelo local. Instala el ZIP de voz o selecciona tu carpeta Whisper en Ajustes.")
    if engine == "openai-whisper" and (not model.endswith(".pt") or not Path(model).is_file()):
        raise RuntimeError("OpenAI Whisper necesita un archivo .pt existente; las carpetas faster-whisper usan otro motor.")
    if engine == "faster-whisper" and model.endswith(".pt"):
        raise RuntimeError("Un archivo .pt necesita el motor OpenAI Whisper, no faster-whisper.")
    return engine, model


def probe_packaged_voice(root):
    """Load shipped engines and Vosk data without opening a microphone."""
    import json
    import os
    from vosk import Model, KaldiRecognizer, SetLogLevel
    from faster_whisper import WhisperModel
    import whisper
    model = Path(root) / 'bundle/models' / VOSK_NAME
    if not is_vosk(model): raise RuntimeError('Falta el modelo Vosk en el instalador.')
    SetLogLevel(-1); recognizer = KaldiRecognizer(Model(str(model)), 16000)
    recognizer.AcceptWaveform(bytes(32000)); json.loads(recognizer.FinalResult())
    result = {'vosk_model':'loaded','faster_whisper':'imported','openai_whisper':'imported','microphone_opened':False}
    if os.name == 'nt':
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        try:
            speaker=win32com.client.Dispatch('SAPI.SpVoice'); voices=speaker.GetVoices()
            if voices.Count == 0: raise RuntimeError('No hay voces de Windows instaladas.')
            result['windows_tts_voices']=voices.Count
        finally: pythoncom.CoUninitialize()
    return result
