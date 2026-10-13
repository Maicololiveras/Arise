"""Fail incomplete base bundles and record exactly which optional tools ship."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from arise_app.gentle_compat import require_compatible_pi


def audit(root):
    root=Path(root);bundle=root/'bundle'
    required=['node/node.exe','node/node_modules/npm/bin/npm-cli.js','node/node_modules/@earendil-works/pi-coding-agent/package.json','node/node_modules/gentle-pi/package.json','python/python.exe','python/Lib/site-packages/pip/__init__.py','media/ffmpeg.exe','media/ffprobe.exe','gh/gh.exe','gentle-installer/scripts/bootstrap.cmd','gentle-installer/bin/arise-result.mjs','models/vosk-model-small-es-0.42/am/final.mdl']
    missing=[name for name in required if not (bundle/name).is_file()]
    if missing:raise RuntimeError('Bundle base incompleto: '+', '.join(missing))
    manifest=json.loads((bundle/'manifest.json').read_text(encoding='utf-8-sig'))
    node=bundle/'node/node_modules'
    shell=json.loads((node/'gentle-pi/package.json').read_text())
    pi=json.loads((node/'@earendil-works/pi-coding-agent/package.json').read_text())
    require_compatible_pi(shell,pi['version'])
    cli=node/'@earendil-works/pi-coding-agent'/pi['bin']['pi']
    if not cli.is_file():raise RuntimeError('Falta el CLI real de Pi.')
    tools={name:('bundled' if name in manifest.get('mcp',{}) else 'download-required') for name in ('forge','screenview','inputcontrol','transcripcion')}
    for name,spec in manifest.get('mcp',{}).items():
        for arg in spec['command']:
            if arg.startswith('@bundle/') and not (bundle/arg[8:]).is_file():raise RuntimeError('MCP incompleto: '+name)
    result={'pi':pi['version'],'gentle':shell['version'],'tools':tools,'all_tools_bundled':all(v=='bundled' for v in tools.values()),'models':'Vosk incluido; Whisper/Piper/Qwen en el ZIP de modelos o Ajustes','accounts':'Proveedor del agente y servicios personales se autentican por el usuario'}
    (bundle/'installation-inventory.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
    return result

if __name__=='__main__':audit(sys.argv[1])
