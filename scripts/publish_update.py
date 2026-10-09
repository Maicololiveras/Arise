"""Publish tested installer then atomically update main's Windows manifest."""
import base64
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from arise_app import __version__
REPO='Maicololiveras/Arise';tag='v'+__version__;commit=os.environ['GITHUB_SHA']
setup=Path('release/dist/ARISE-Setup.exe')
if not setup.is_file():raise RuntimeError('Tested installer artifact missing')
notes=Path('packaging/RELEASE-NOTES.md').read_text(encoding='utf-8')
digest=hashlib.sha256(setup.read_bytes()).hexdigest()
checksum=setup.with_suffix('.exe.sha256');checksum.write_text(digest+'  ARISE-Setup.exe\n')
def gh(*args):return subprocess.run(['gh',*args],check=True,text=True,capture_output=True).stdout
# A version is immutable: bump it instead of replacing an already-published asset.
existing=subprocess.run(['gh','release','view',tag,'--repo',REPO],capture_output=True,text=True)
if existing.returncode==0:raise RuntimeError('Version already published; increment __version__ before creating another release.')
gh('release','create',tag,str(setup),str(checksum),'--repo',REPO,'--target',commit,'--title','ARISE Assistant '+__version__,'--notes-file','packaging/RELEASE-NOTES.md')
release=json.loads(gh('api',f'repos/{REPO}/releases/tags/{tag}'))
asset=next(a for a in release['assets'] if a['name']=='ARISE-Setup.exe')
manifest={'schema':1,'version':__version__,'notes':notes[:12000],'installer_url':asset['browser_download_url'],'asset_id':asset['id'],'sha256':digest,'size':asset['size'],'source_commit':commit}
try:old=json.loads(gh('api',f'repos/{REPO}/contents/updates/windows.json?ref=main'))
except subprocess.CalledProcessError:old=None
payload={'message':f'Publish tested Windows update {tag} [skip ci]','branch':'main','content':base64.b64encode((json.dumps(manifest,indent=2)+'\n').encode()).decode()}
if old:payload['sha']=old['sha']
file=Path('main-update-request.json');file.write_text(json.dumps(payload))
gh('api',f'repos/{REPO}/contents/updates/windows.json','--method','PUT','--input',str(file))
print('Published '+tag+' and main/updates/windows.json (no application source merged).')
