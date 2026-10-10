"""Forge owns speech transport; ARISE owns microphone, playback and task consent."""
import asyncio
import json
import os
import time
from pathlib import Path
from .processes import JsonProcess


def voice_command(runtime):
    spec=runtime.storage.config.get('mcp',{}).get('forge',{})
    command=spec.get('command',[])
    if not spec.get('enabled') or len(command)!=2:
        raise RuntimeError('Instala o repara Forge para activar su voz.')
    entry=Path(command[1]).parent.parent/'voice/forge-voice.js'
    if not entry.is_file():raise RuntimeError('Actualiza Forge: esta versión no incluye el puente de voz.')
    if runtime.storage.config.get('piper_model'):
        try: ready=json.loads((entry.parent/'capabilities.json').read_text()).get('neural_piper') is True
        except (OSError,ValueError): ready=False
        if not ready: raise RuntimeError('Actualiza Forge desde Instalar y reparar dependencias para usar la voz neuronal.')
    return [command[0],str(entry)]


def speak(runtime,text,voice,cancel,active,shutdown):
    process=JsonProcess(voice_command(runtime),cwd=runtime.storage.config['workspace'])
    try:
        # The response arrives only when local playback finishes, not on spawn.
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(process.request,{'type':'speak','text':text[:10000],'voice':voice},300)
            while not future.done():
                if cancel.is_set() or not active.is_set() or shutdown.is_set():
                    process.request({'type':'cancel'},timeout=3)
                    return
                shutdown.wait(.05)
            future.result()
    finally:process.close()


def synthesize(runtime, text, executable, model, output, cancel, active, shutdown):
    """Forge owns the neural synthesizer; ARISE owns interruptible playback."""
    import concurrent.futures
    process=JsonProcess(voice_command(runtime),cwd=runtime.storage.config['workspace'])
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(process.request,{'type':'synthesize','text':text[:10000],
                'executable':str(executable),'model':str(model),'output':str(output)},70)
            while not future.done():
                if cancel.is_set() or not active.is_set() or shutdown.is_set():
                    process.request({'type':'cancel'},timeout=3)
                    return False
                shutdown.wait(.05)
            future.result()
            return True
    finally:process.close()


class ForgeConnection:
    def __init__(self,runtime,backend,model,url):
        self.runtime,self.backend,self.model,self.url=runtime,backend,model,url
        self.process=None;self.queue=None;self.closed=False
    def __call__(self,*args,**kwargs):return self
    async def __aenter__(self):
        loop=asyncio.get_running_loop();self.queue=asyncio.Queue(maxsize=128)
        def receive(record):
            if record.get('type')=='voice_event':loop.call_soon_threadsafe(deliver,record['event'])
            elif record.get('type')=='process_closed':loop.call_soon_threadsafe(deliver,{'type':'forge.closed'})
        def deliver(event):
            if self.closed:return
            if self.queue.full():
                self.queue.get_nowait()
                event={'type':'error','error':{'message':'El audio de Forge excedió la cola de reproducción.'}}
            self.queue.put_nowait(event)
        env={key:value for key,value in os.environ.items() if key not in ('GH_TOKEN','GITHUB_TOKEN','OPENAI_API_KEY','ANTHROPIC_API_KEY','GEMINI_API_KEY','FORGE_OPENAI_API_KEY','FORGE_LOCAL_API_KEY')}
        key=self.runtime.credentials.get('openai' if self.backend=='openai' else 'forge-local')
        if key:env['FORGE_OPENAI_API_KEY' if self.backend=='openai' else 'FORGE_LOCAL_API_KEY']=key
        self.process=JsonProcess(voice_command(self.runtime),env=env,cwd=self.runtime.storage.config['workspace'],on_event=receive)
        try:
            await asyncio.to_thread(self.process.request,{'type':'connect','config':{'backend':self.backend,'model':self.model,'url':self.url}},20)
        except Exception:
            await self.close();raise
        return self
    async def send(self,raw):
        await asyncio.to_thread(self.process.send,{'type':'event','event':json.loads(raw)})
    async def recv(self):
        event=await self.queue.get()
        if event.get('type')=='forge.closed':raise RuntimeError('Forge cerró la sesión de voz.')
        return json.dumps(event)
    def __aiter__(self):return self
    async def __anext__(self):
        if self.closed:raise StopAsyncIteration
        return await self.recv()
    async def close(self):
        if self.closed:return
        self.closed=True
        if self.process:await asyncio.to_thread(self.process.close)
    async def __aexit__(self,*args):await self.close()
