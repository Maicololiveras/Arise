"""Publish only a verified binary ZIP, checksum and manifest to Arise."""
import base64
import json
from pathlib import Path
import subprocess
import sys

REPO = 'Maicololiveras/Arise'
def gh(*args):
    return subprocess.check_output(['gh', *args], text=True)

m = json.loads(Path('out/manifest.json').read_text())
tag = m['tag']; tool = m['tool']
asset = Path('out') / m['url'].rsplit('/', 1)[1]
# Never mutate a released version. A retry reuses it only if its checksum agrees.
try:
    release = json.loads(gh('release', 'view', tag, '--repo', REPO, '--json', 'assets'))
except subprocess.CalledProcessError:
    gh('release', 'create', tag, str(asset), str(asset) + '.sha256', '--repo', REPO,
       '--target', 'herramientas', '--latest=false', '--title', tool + ' Windows ' + m['version'],
       '--notes', 'Paquete Windows x64. Catálogo MCP verificado. Instalación: rama herramientas.')
else:
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        gh('release', 'download', tag, '--repo', REPO, '--pattern', asset.name + '.sha256', '--dir', tmp)
        if (Path(tmp) / (asset.name + '.sha256')).read_text().split()[0] != m['sha256']:
            raise RuntimeError('Version already published with a different checksum')
path = f'repos/{REPO}/contents/manifests/{tool}.json'
old = json.loads(gh('api', path + '?ref=herramientas'))
request = {'message': f'Publish {tag}', 'branch': 'herramientas', 'sha': old['sha'],
           'content': base64.b64encode((json.dumps(m, indent=2) + '\n').encode()).decode()}
Path('publish-request.json').write_text(json.dumps(request))
gh('api', path, '--method', 'PUT', '--input', 'publish-request.json')
print('Published ' + tag)
