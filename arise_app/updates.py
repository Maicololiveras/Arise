"""Channel-controlled updates: verified installer, external launcher, consent in native UI."""
from __future__ import annotations
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from . import __version__

MANIFEST_URL = 'https://api.github.com/repos/Maicololiveras/Arise/contents/updates/windows.json?ref=main'
RELEASE_ROOT = 'https://github.com/Maicololiveras/Arise/releases/download/'
MAX_INSTALLER = 2 * 1024**3

def build_channel():
    marker = Path(__file__).parent / 'resources/update-channel.json'
    channel = json.loads(marker.read_text(encoding='utf-8')).get('channel') if marker.is_file() else 'main'
    if channel not in ('main', 'qa'): raise ValueError('Canal de actualizaciones inválido.')
    return channel

def version_tuple(value):
    if not isinstance(value, str) or not re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)', value):
        raise ValueError('Versión de actualización inválida.')
    return tuple(map(int, value.split('.')))

def validate_manifest(data, current=__version__, channel=None):
    channel = channel or build_channel()
    if channel not in ('main', 'qa'): raise ValueError('Canal inválido.')
    if not isinstance(data, dict) or data.get('schema') != 1: raise ValueError('Manifiesto de actualización incompatible.')
    if data.get('channel', 'main') != channel: raise ValueError('La actualización pertenece a otro canal.')
    version = data.get('version'); target = version_tuple(version)
    if target <= version_tuple(current): return None
    expected = RELEASE_ROOT + ('qa-v' if channel == 'qa' else 'v') + version + '/ARISE-Setup.exe'
    if data.get('installer_url') != expected: raise ValueError('El instalador no pertenece a una versión oficial de ARISE.')
    if not isinstance(data.get('sha256'), str) or not re.fullmatch('[a-f0-9]{64}', data['sha256']): raise ValueError('Falta el hash del instalador.')
    if type(data.get('size')) is not int or not 0 < data['size'] <= MAX_INSTALLER: raise ValueError('Tamaño de instalador inválido.')
    if not isinstance(data.get('notes'), str) or len(data['notes']) > 12000: raise ValueError('Novedades inválidas.')
    if type(data.get('asset_id')) is not int or data['asset_id']<=0: raise ValueError('Identificador de instalador inválido.')
    return data

def check_update(current=__version__, opener=urllib.request.urlopen, channel=None):
    channel = channel or build_channel()
    if channel not in ('main', 'qa'): raise ValueError('Canal inválido.')
    url = MANIFEST_URL.replace('ref=main', 'ref=' + channel)
    request = urllib.request.Request(url, headers={'User-Agent':'ARISE/'+current, 'Cache-Control':'no-cache','Accept':'application/vnd.github.raw+json'})
    with opener(request, timeout=8) as response:
        raw = response.read(128*1024+1)
    if len(raw) > 128*1024: raise ValueError('Manifiesto demasiado grande.')
    return validate_manifest(json.loads(raw), current, channel)

def download_update(manifest, root, opener=urllib.request.urlopen, channel=None):
    manifest = validate_manifest(manifest, channel=channel)
    if not manifest: raise ValueError('La versión ya está instalada.')
    folder = Path(root) / 'updates' / manifest['version']; folder.mkdir(parents=True, exist_ok=True)
    target = folder / 'ARISE-Setup.exe'; temporary = folder / 'ARISE-Setup.download'
    digest = hashlib.sha256(); size = 0
    try:
        request = urllib.request.Request('https://api.github.com/repos/Maicololiveras/Arise/releases/assets/'+str(manifest['asset_id']), headers={'User-Agent':'ARISE/'+__version__, 'Accept':'application/octet-stream'})
        with opener(request, timeout=30) as response, temporary.open('wb') as output:
            if response.geturl().split(':',1)[0] != 'https': raise ValueError('La descarga debe usar HTTPS.')
            while True:
                block = response.read(1024*1024)
                if not block: break
                size += len(block)
                if size > manifest['size']: raise ValueError('La descarga supera el tamaño publicado.')
                digest.update(block); output.write(block)
        if size != manifest['size'] or digest.hexdigest() != manifest['sha256']: raise ValueError('El instalador no coincide con el SHA-256 publicado en su canal.')
        with temporary.open('rb') as file:
            if file.read(2) != b'MZ': raise ValueError('El archivo no es un instalador Windows.')
        os.replace(temporary, target)
        return target
    finally: temporary.unlink(missing_ok=True)

def launch_update(installer, manifest, data_root, install_dir):
    if os.name != 'nt' or not getattr(sys,'frozen',False): raise RuntimeError('La actualización automática requiere la versión instalada para Windows.')
    import psutil
    folder = Path(tempfile.mkdtemp(prefix='arise-update-'))
    resources = Path(__file__).parent / 'resources'
    for name in ('update-launcher.ps1','stop-arise.ps1'): shutil.copy2(resources/name, folder/name)
    plan = {'installer':str(Path(installer).resolve()),'sha256':manifest['sha256'],'install_dir':str(Path(install_dir).resolve()),'data_dir':str(Path(data_root).resolve()),'ui_pid':os.getpid(),'ui_started':psutil.Process().create_time()}
    (folder/'plan.json').write_text(json.dumps(plan), encoding='utf-8')
    powershell = Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
    subprocess.Popen([str(powershell),'-NoProfile','-ExecutionPolicy','Bypass','-File',str(folder/'update-launcher.ps1'),'-Plan',str(folder/'plan.json')], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP)
    return folder

def shutdown_application(root, timeout=30):
    """Ask the existing UI/daemon to close; never start an instance just to stop it."""
    from PySide6.QtCore import QCoreApplication
    from PySide6.QtNetwork import QLocalSocket
    from .daemon import read_descriptor
    from .remote import RemoteAssistant
    import psutil
    app = QCoreApplication.instance() or QCoreApplication([])
    address = 'ARISE-' + hashlib.sha256(str(Path(root).resolve()).encode()).hexdigest()[:20]
    client = QLocalSocket(); client.connectToServer(address)
    connected = client.waitForConnected(500)
    if connected:
        client.write(b'shutdown\n'); client.flush(); client.waitForBytesWritten(1000); client.disconnectFromServer()
    descriptor = read_descriptor(root)
    process = None
    if descriptor:
        try: process = psutil.Process(descriptor['pid'])
        except psutil.NoSuchProcess: pass
        try: RemoteAssistant(descriptor, root).shutdown()
        except RuntimeError: pass  # UI may already have requested the same shutdown
    deadline = time.monotonic() + timeout
    if process:
        try: process.wait(timeout=max(.1, deadline-time.monotonic()))
        except psutil.TimeoutExpired: return 1
    while connected and time.monotonic() < deadline:
        probe = QLocalSocket(); probe.connectToServer(address)
        connected = probe.waitForConnected(200); probe.abort()
        if connected: time.sleep(.1)
    return 1 if connected else 0
