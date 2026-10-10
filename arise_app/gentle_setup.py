"""Run the official interactive installer and adopt only its verified result."""
import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from .bundle import application_root

LOCK=threading.Lock()

def wait_for_installer(process, result_file, log_file, timeout):
    deadline=time.monotonic()+timeout
    while not result_file.is_file():
        code=process.poll()
        if code is not None:
            # The result reporter writes atomically; allow its final rename.
            if result_file.is_file():break
            tail=''
            try:
                with log_file.open('rb') as stream:
                    stream.seek(0,2);size=stream.tell();stream.seek(max(0,size-8192))
                    tail=stream.read().decode('utf-8',errors='replace')
            except OSError:pass
            reason=' Los permisos de la carpeta temporal fueron rechazados (acl-mask).' if 'acl-mask' in tail else ''
            raise RuntimeError(f'El instalador de Gentle terminó (código {code}) sin confirmar la instalación.{reason} Diagnóstico: {log_file}')
        if time.monotonic()>=deadline:
            raise RuntimeError(f'El instalador sigue abierto sin confirmar. Revisa su ventana antes de reintentar. Diagnóstico: {log_file}')
        time.sleep(.5)

def validate_result(result, node):
    if result.get('status')!='ready':
        raise RuntimeError('Gentle no completó la instalación: '+str(result.get('reason','sin resultado'))[:200])
    if result.get('channel') not in ('release','main'):raise ValueError('Canal de Gentle inválido.')
    roots=[Path(result[key]) for key in ('pi_root','gentle_root','agent_home')]
    if not all(path.is_absolute() and path.is_dir() for path in roots):raise ValueError('Faltan carpetas de la instalación de Gentle.')
    pi,gentle,home=roots
    metadata=json.loads((pi/'package.json').read_text(encoding='utf-8'))
    shell=json.loads((gentle/'package.json').read_text(encoding='utf-8'))
    if metadata.get('name')!='@earendil-works/pi-coding-agent' or shell.get('name') not in ('gentle-pi','gentle-shell'):
        raise ValueError('Los paquetes instalados no corresponden a Pi/Gentle.')
    cli=(pi/metadata['bin']['pi']).resolve()
    if not cli.is_relative_to(pi.resolve()) or not cli.is_file() or not (gentle/'extensions').is_dir() or not Path(node).is_file():
        raise ValueError('La instalación de Pi/Gentle está incompleta.')
    return {'pi_command':[str(node),str(cli)],'gentle_path':str(gentle),'gentle_agent_home':str(home),'gentle_channel':result['channel']}

def install_gentle(runtime, timeout=3600):
    if os.name!='nt':raise RuntimeError('Este instalador de Gentle requiere Windows.')
    if not LOCK.acquire(blocking=False):raise RuntimeError('El instalador de Gentle ya está abierto.')
    try:
        with runtime.transition_lock:
            if runtime.busy:raise RuntimeError('Detén la tarea activa antes de instalar Gentle.')
            runtime.disconnect()
        bundle=application_root()/'bundle'
        source=bundle/'gentle-installer'
        if not (source/'scripts/bootstrap.cmd').is_file():raise RuntimeError('Usa el ZIP nuevo de ARISE: falta el instalador oficial de Gentle.')
        jobs=runtime.storage.root/'installers';jobs.mkdir(exist_ok=True)
        # Keep the job if the UI closes; the installer may still own files in it.
        job=Path(tempfile.mkdtemp(prefix='gentle-',dir=jobs))
        shutil.copytree(source,job,dirs_exist_ok=True)
        runtime.emit('notice',{'text':'Se abrirá el instalador oficial. Elige versión estable o último main y confirma su plan. ARISE verificará el resultado.'})
        result_file=job/'arise-result.json'
        log_file=job/'bootstrap.log'
        command=str(Path(os.environ['SystemRoot'])/'System32/cmd.exe')
        with log_file.open('wb') as log:
            process=subprocess.Popen([command,'/d','/c','bootstrap.cmd'],cwd=str(job/'scripts'),
                stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            runtime.emit('notice',{'text':f'Preparando Gentle. El asistente se abrirá en el navegador. Diagnóstico: {log_file}'})
            wait_for_installer(process,result_file,log_file,timeout)
        result=json.loads(result_file.read_text(encoding='utf-8'))
        changes=validate_result(result,bundle/'node/node.exe')
        with runtime.transition_lock:
            if runtime.busy:raise RuntimeError('Gentle está instalado. Detén la tarea y vuelve a configurar para conectarlo.')
            previous={key:runtime.storage.config.get(key,'') for key in changes}
            runtime.settings(changes)
            try:
                if not runtime.connect_pi().get('gentleVerified'):
                    raise RuntimeError('Pi inició, pero no registró los comandos de Gentle.')
            except Exception:
                runtime.settings(previous)
                raise
        runtime.emit('notice',{'text':'Gentle '+result['channel']+' instalado y conectado. Sus comandos se verificaron en Pi.'})
        from .tool_setup import auto_setup
        auto_setup(runtime)
        return {'installed':True,'channel':result['channel'],'version':result.get('version'),'verified':True}
    finally:LOCK.release()
