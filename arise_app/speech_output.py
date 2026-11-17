"""Bounded sentence synthesis with one chunk of look-ahead; no transcript cache."""
import concurrent.futures
import re
import shutil
import subprocess
import tempfile
import threading
import wave
import time
from pathlib import Path


def speech_chunks(text,first=180,following=360):
    text=' '.join(text[:10000].split());result=[]
    while text:
        limit=first if not result else following
        if len(text)<=limit:result.append(text);break
        candidates=list(re.finditer(r'[.!?;:]\s+',text[:limit+1]))
        end=candidates[-1].end() if candidates else text.rfind(' ',0,limit+1)
        if end<=0:end=limit
        result.append(text[:end].strip());text=text[end:].lstrip()
    return result


def render_edge(voice,text,cancel):
    from .bundle import application_root
    from .forge_voice import edge_audio, EdgeAudioSession
    from .voice_metrics import current_trace
    trace=current_trace()
    from .platforms import bundled_executable
    ffmpeg=bundled_executable(application_root(),'bundle/media/ffmpeg')
    executable=str(ffmpeg) if ffmpeg.is_file() else shutil.which('ffmpeg')
    try:
        import miniaudio
    except ImportError:
        miniaudio=None
    if not executable and miniaudio is None:raise RuntimeError('Falta el decodificador de audio. Repara ARISE.')
    parts=speech_chunks(text) if voice.runtime.storage.config.get('voice_fluent',True) else [text[:10000]]
    abort=threading.Event();started=False
    class Cancel:
        def is_set(self):return abort.is_set() or cancel.is_set()
    combined=Cancel()
    def stopped():return combined.is_set() or not voice.active.is_set() or voice.shutdown.is_set()
    with EdgeAudioSession() as session,tempfile.TemporaryDirectory() as temporary,concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        def prepare(index):
            mp3=Path(temporary)/f'{index}.mp3';wavfile=mp3.with_suffix('.wav')
            synthesis_started=time.monotonic()
            if stopped() or not edge_audio(voice.runtime,parts[index],mp3,combined,voice.active,voice.shutdown,session=session):return None
            if trace:trace.record("synthesis",synthesis_started,chunk=index)
            if miniaudio is not None:
                decoded=miniaudio.decode_file(str(mp3),output_format=miniaudio.SampleFormat.SIGNED16,nchannels=1,sample_rate=24000)
                return decoded.samples.tobytes(),24000
            process=subprocess.Popen([executable,'-y','-i',str(mp3),'-ac','1','-ar','24000',str(wavfile)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            deadline=time.monotonic()+30
            try:
                while process.poll() is None:
                    if stopped():return None
                    if time.monotonic()>deadline:raise RuntimeError('La preparación del audio agotó el tiempo de espera.')
                    voice.shutdown.wait(.025)
                if process.returncode:raise RuntimeError('No se pudo preparar el audio de Gonzalo.')
            finally:
                if process.poll() is None:process.kill();process.wait(timeout=3)
            with wave.open(str(wavfile)) as wav:return wav.readframes(wav.getnframes()),wav.getframerate()
        try:
            future=pool.submit(prepare,0) if parts else None
            for index in range(len(parts)):
                while not future.done():
                    if stopped():return False
                    voice.shutdown.wait(.025)
                audio=future.result()
                if stopped() or audio is None:return False
                if index+1<len(parts):future=pool.submit(prepare,index+1)
                playback_started=time.monotonic()
                voice.audio.play(audio[0],rate=audio[1]);started=True
                if trace and index==0:trace.record("first_playback",trace.started)
                voice.runtime.orb.update('speaking',microphone=not getattr(voice,'preview_only',False))
                while voice.audio.speaking:
                    if stopped():voice.audio.interrupt();return False
                    voice.shutdown.wait(.025)
                if trace:trace.record("playback",playback_started,chunk=index)
            return True
        except Exception as error:
            error.audio_started=started
            raise
        finally:
            abort.set()
            if stopped():voice.audio.interrupt()
