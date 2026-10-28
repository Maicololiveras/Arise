"""Official Engram release updates. Never touch memory databases or disable TLS."""
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import tempfile
import urllib.request
import zipfile

REPOSITORY = 'Gentleman-Programming/engram'
API = 'https://api.github.com/repos/'+REPOSITORY+'/releases/latest'


def fetch(url, limit):
    request = urllib.request.Request(url, headers={'User-Agent':'ARISE-Engram-updater','Accept':'application/vnd.github+json' if url==API else 'application/octet-stream'})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read(limit+1)
    if len(data)>limit: raise ValueError('La descarga de Engram excede el tamaño permitido.')
    return data


def release_plan(release, machine):
    tag = release.get('tag_name','')
    if release.get('draft') or release.get('prerelease') or not re.fullmatch(r'v\d+\.\d+\.\d+',tag):
        raise ValueError('La release de Engram no es una versión estable reconocida.')
    architecture = {'amd64':'amd64','x86_64':'amd64','arm64':'arm64','aarch64':'arm64'}.get(machine.lower())
    if not architecture: raise ValueError('Engram requiere Windows x64 o ARM64.')
    version=tag[1:]
    name=f'engram_{version}_windows_{architecture}.zip'
    base=f'https://github.com/{REPOSITORY}/releases/download/{tag}/'
    assets={a.get('name'):a.get('browser_download_url') for a in release.get('assets',[])}
    if assets.get(name)!=base+name or assets.get('checksums.txt')!=base+'checksums.txt':
        raise ValueError('La release no contiene los archivos oficiales esperados para Windows.')
    return version,name,base+name,base+'checksums.txt'


def verified_executable(archive, checksums, name):
    expected=[]
    for line in checksums.decode('utf-8').splitlines():
        parts=line.split()
        if len(parts)==2 and parts[1].lstrip('*')==name and re.fullmatch('[a-fA-F0-9]{64}',parts[0]):
            expected.append(parts[0].lower())
    if len(expected)!=1 or hashlib.sha256(archive).hexdigest()!=expected[0]:
        raise ValueError('Checksum de Engram incorrecto. No se instaló ni ejecutó la descarga.')
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        entries=[i for i in z.infolist() if i.filename=='engram.exe']
        if len(entries)!=1 or entries[0].file_size>100*1024*1024:
            raise ValueError('El ZIP no contiene un único engram.exe válido.')
        # Read only the exact leaf; no archive paths are extracted.
        content=z.read(entries[0])
        if not content.startswith(b'MZ'): raise ValueError('El archivo no es un ejecutable Windows.')
        return content


def engine_environment(env, config):
    """Explicit selection wins; otherwise reuse the official Windows install."""
    result=dict(env)
    selected=config.get('engram_bin') or result.get('ENGRAM_BIN')
    if not selected and result.get('LOCALAPPDATA'):
        known=Path(result['LOCALAPPDATA'])/'engram/bin/engram.exe'
        if known.is_file(): selected=str(known)
    if selected:
        path=Path(selected)
        if not path.is_absolute() or not path.is_file():
            raise RuntimeError('La ruta ENGRAM_BIN configurada no existe. Repara Engram desde Ajustes.')
        result['ENGRAM_BIN']=str(path)
        result['PATH']=str(path.parent)+os.pathsep+result.get('PATH','')
    return result


def update_engram(runtime):
    if os.name!='nt': raise RuntimeError('La actualización de Engram desde ARISE requiere Windows.')
    from .gentle_setup import LOCK
    if not LOCK.acquire(blocking=False): raise RuntimeError('Hay otra instalación de Gentle/Engram activa.')
    try:
        # Hold chat transitions during adoption, and do not interrupt an active task.
        with runtime.transition_lock:
            if runtime.busy or runtime.pi_has_children or any(j['process'].poll() is None for j in runtime.terminals.jobs.values()):
                raise RuntimeError('Detén las tareas y subagentes antes de actualizar Engram.')
            runtime.emit('notice',{'text':'Consultando la última release estable de Engram en Gentleman-Programming/engram…'})
            version,name,url,sums=release_plan(json.loads(fetch(API,1024*1024)),platform.machine())
            content=verified_executable(fetch(url,64*1024*1024),fetch(sums,1024*1024),name)
            root=runtime.storage.root/'tools/engram';root.mkdir(parents=True,exist_ok=True)
            directory=Path(tempfile.mkdtemp(prefix=version+'-',dir=root))
            binary=directory/'engram.exe';binary.write_bytes(content)
            check=subprocess.run([str(binary),'--version'],capture_output=True,text=True,timeout=30,
                                 creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if check.returncode or not re.search(r'(?im)^engram\s+v?'+re.escape(version)+r'\s*$',check.stdout):
                raise RuntimeError('El binario descargado no confirmó la versión esperada. Se conservó la selección anterior.')
            previous=runtime.storage.config.get('engram_bin','')
            runtime.disconnect_pi()
            try:
                runtime.settings({'engram_bin':str(binary)})
            except Exception:
                runtime.storage.config['engram_bin']=previous
                raise
            runtime.emit('notice',{'text':f'Engram {version} descargado, checksum y ejecutable verificados. ARISE usará {binary}. No se modificaron memorias ni se detuvieron servidores externos. Ejecuta mem_doctor para comprobar el proveedor activo.'})
            return {'version':version,'binary':str(binary),'binary_verified':True,'provider_verified':False}
    finally: LOCK.release()
