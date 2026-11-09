"""Publish a tested release and update only its own branch manifest."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from arise_app import __version__
REPO='Maicololiveras/Arise';commit=os.environ['GITHUB_SHA']
channel=os.environ['GITHUB_REF_NAME']
if channel not in ('main','qa'): raise RuntimeError('Publish only from qa or main')
tag=('qa-v' if channel=='qa' else 'v')+__version__
setup=Path('release/dist/ARISE-Setup.exe')
if not setup.is_file():raise RuntimeError('Tested installer artifact missing')
notes=Path('packaging/RELEASE-NOTES.md').read_text(encoding='utf-8')
notes = '# ARISE ' + __version__ + (' QA' if channel == 'qa' else '') + '\n' + notes.partition('\n')[2]
Path('packaging/RELEASE-NOTES.md').write_text(notes, encoding='utf-8')
digest=hashlib.sha256(setup.read_bytes()).hexdigest()
checksum=setup.with_suffix('.exe.sha256');checksum.write_text(digest+'  ARISE-Setup.exe\n')
def gh(*args):return subprocess.run(['gh',*args],check=True,text=True,capture_output=True).stdout
# A version is immutable: bump it instead of replacing an already-published asset.
existing=subprocess.run(['gh','release','view',tag,'--repo',REPO],capture_output=True,text=True)
if existing.returncode==0:raise RuntimeError('Version already published; increment __version__ before creating another release.')
complete=Path('release/complete/ARISE-Windows-Complete.zip')
if not complete.is_file(): raise RuntimeError('Complete ZIP artifact missing')
flags=['--prerelease','--latest=false'] if channel=='qa' else ['--latest']
assets=[str(setup),str(checksum)]
if complete.stat().st_size < 2*1024**3: assets.append(str(complete))
else:
    with open('packaging/RELEASE-NOTES.md','a') as output:
        output.write('\nZIP completo: https://github.com/'+REPO+'/actions/runs/'+os.environ['GITHUB_RUN_ID']+' (artefacto ARISE-Windows-Complete).\n')
gh('release','create',tag,*assets,'--repo',REPO,'--target',commit,'--title','ARISE '+channel+' '+__version__,'--notes-file','packaging/RELEASE-NOTES.md',*flags)
release=json.loads(gh('api',f'repos/{REPO}/releases/tags/{tag}'))
asset=next(a for a in release['assets'] if a['name']=='ARISE-Setup.exe')
manifest={'schema':1,'channel':channel,'version':__version__,'notes':notes[:12000],'installer_url':asset['browser_download_url'],'asset_id':asset['id'],'sha256':digest,'size':asset['size'],'source_commit':commit}
# Publish links only after the release and verified installer asset exist.
from scripts.release_readme import publish_metadata

def api(endpoint, payload=None, method='POST'):
    if payload is None:
        return json.loads(gh('api', endpoint))
    file = Path('channel-update-request.json')
    file.write_text(json.dumps(payload), encoding='utf-8')
    return json.loads(gh('api', endpoint, '--method', method, '--input', str(file)))

publish_metadata(api, channel, manifest, sync_other=channel != "qa")
print('Published '+tag+'; channel manifest and README download links synchronized')
