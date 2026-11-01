"""Download versioned Windows binaries from the public herramientas distribution."""
import hashlib
import json
from pathlib import Path
import re
import urllib.request
import zipfile
from .https import open_https

TOOLS = {'forge': 'forge-mcp', 'screenview': 'screenview-mcp', 'inputcontrol': 'inputcontrol-mcp'}
BASE = 'https://raw.githubusercontent.com/Maicololiveras/Arise/herramientas/manifests/'


def fetch_manifest(name, opener=None):
    # Never use github_opener here: public downloads must not carry credentials.
    opener = opener or open_https
    package = TOOLS[name]
    with opener(BASE + name + '.json', timeout=30) as response:
        raw = response.read(65537)
    if len(raw) > 65536:
        raise RuntimeError('Manifiesto público demasiado grande.')
    manifest = json.loads(raw)
    if not isinstance(manifest, dict): raise RuntimeError('Manifiesto público inválido.')
    if manifest.get('status') == 'pending':
        raise RuntimeError(f'{package}: el paquete público todavía no está publicado en Arise/herramientas. Reintenta después de su publicación; no necesitas autenticarte con GitHub.')
    tag = manifest.get('tag', '')
    if (manifest.get('schema') != 1 or manifest.get('tool') != name
        or manifest.get('platform') != 'windows-x64'
        or not isinstance(tag, str) or not re.fullmatch(r'herramientas-' + name + r'-v\d+\.\d+\.\d+-[a-f0-9]{12}', tag)
        or not isinstance(manifest.get('sha256'), str) or not re.fullmatch(r'[a-f0-9]{64}', manifest['sha256'])
        or type(manifest.get('size')) is not int or not 0 < manifest['size'] <= 1_073_741_824
        or manifest.get('entry') != package + '.exe'):
        raise RuntimeError('Manifiesto público inválido: ' + name)
    url = f'https://github.com/Maicololiveras/Arise/releases/download/{tag}/{package}-windows-x64.zip'
    if manifest.get('url') != url:
        raise RuntimeError('Origen de descarga no autorizado: ' + name)
    return manifest


def install_public_tool(name, root, notify=lambda message: None, opener=None):
    opener = opener or open_https
    manifest = fetch_manifest(name, opener)
    package = TOOLS[name]
    url = manifest['url']
    root = Path(root); root.mkdir(parents=True, exist_ok=True)
    archive = root / (name + '.zip')
    digest = hashlib.sha256(); size = 0
    notify(f'Descargando {package} desde la distribución pública…')
    try:
        with opener(url, timeout=60) as response, archive.open('wb') as output:
            while block := response.read(1024 * 1024):
                size += len(block)
                if size > manifest['size']:
                    raise RuntimeError('Tamaño de descarga incorrecto: ' + name)
                digest.update(block); output.write(block)
        if size != manifest['size'] or digest.hexdigest() != manifest['sha256']:
            raise RuntimeError('Descarga incompleta o SHA-256 incorrecto: ' + name)
        target = root / name
        with zipfile.ZipFile(archive) as z:
            total = 0; seen = set()
            for item in z.infolist():
                path = item.filename.replace('\\', '/')
                parts = path.split('/')
                total += item.file_size
                if (path.startswith('/') or ':' in path or any(p in ('.', '..') for p in parts)
                    or any(p.endswith((' ', '.')) for p in parts if p)
                    or re.search(r'[<>"|?*]', path)
                    or re.search(r'(^|/)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\.|/|$)', path, re.I)
                    or path.casefold() in seen or total > 2_147_483_648
                    or (item.external_attr >> 16) & 0o170000 == 0o120000):
                    raise RuntimeError('Ruta o contenido ZIP inválido: ' + name)
                seen.add(path.casefold())
            z.extractall(target)
        entry = target / manifest['entry']
        if not entry.is_file():
            raise RuntimeError('Falta el ejecutable público: ' + name)
        return {'command': [str(entry)], 'enabled': True}, manifest
    finally:
        archive.unlink(missing_ok=True)
