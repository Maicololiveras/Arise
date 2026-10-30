"""Explicit mobile audio requests, processed on the PC; no microphone on the PC."""
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import wave

LOCK=threading.Lock()
MODEL=None
MODEL_KEY=None


def transcribe(config, audio):
    if not LOCK.acquire(blocking=False): raise RuntimeError('El PC está procesando otro audio; espera un momento.')
    try:
        with wave.open(io.BytesIO(audio),'rb') as wav:
            if wav.getnchannels()!=1 or wav.getsampwidth()!=2 or wav.getframerate()!=16000 or not 0<wav.getnframes()<=16000*30:
                raise ValueError('Audio inválido: máximo 30 segundos, mono PCM16 a 16 kHz.')
            pcm=wav.readframes(wav.getnframes())
            if len(pcm)!=wav.getnframes()*2: raise ValueError('Audio incompleto.')
        from .models import resolve_stt
        engine,model=resolve_stt(config)
        global MODEL,MODEL_KEY
        if MODEL_KEY!=(engine,model):
            if engine=='vosk':
                from vosk import Model
                loaded=Model(model)
            elif engine=='openai-whisper':
                import whisper
                loaded=whisper.load_model(model,device='cpu')
            else:
                from faster_whisper import WhisperModel
                loaded=WhisperModel(model,device='cpu',compute_type='int8',local_files_only=True)
            MODEL,MODEL_KEY=loaded,(engine,model)
        if engine=='vosk':
            from vosk import KaldiRecognizer
            recognizer=KaldiRecognizer(MODEL,16000);recognizer.AcceptWaveform(pcm)
            return json.loads(recognizer.FinalResult()).get('text','')
        import numpy as np
        samples=np.frombuffer(pcm,dtype='<i2').astype(np.float32)/32768
        if engine=='openai-whisper': return MODEL.transcribe(samples,language='es',fp16=False).get('text','').strip()
        segments,_=MODEL.transcribe(samples,language='es',vad_filter=True)
        return ' '.join(s.text for s in segments).strip()
    finally: LOCK.release()


def speak(text):
    if os.name!='nt': raise RuntimeError('La voz de respuesta de esta versión requiere Windows.')
    if not LOCK.acquire(blocking=False): raise RuntimeError('El PC está procesando otro audio.')
    try:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        try:
            with tempfile.TemporaryDirectory(prefix='arise-mobile-voice-') as directory:
                path=str(Path(directory)/'reply.wav')
                stream=win32com.client.Dispatch('SAPI.SpFileStream')
                speaker=win32com.client.Dispatch('SAPI.SpVoice')
                stream.Open(path,3)
                try:
                    speaker.AudioOutputStream=stream
                    # SVSFIsNotXML: model output is spoken as text, never speech markup.
                    speaker.Speak(text[:4000],16)
                finally: stream.Close()
                return Path(path).read_bytes()
        finally: pythoncom.CoUninitialize()
    finally: LOCK.release()
