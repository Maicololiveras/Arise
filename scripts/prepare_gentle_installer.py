"""Bundle the pinned official Windows wizard, with a result-only ARISE adapter."""
import argparse
import hashlib
import shutil
import tempfile
import urllib.request
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from arise_app.downloads import safe_extract

URL='https://github.com/Gentleman-Programming/gentle-shell/releases/download/v4.0.0/gentle-shell-installer-windows.zip'
SHA256='e80d6af7bc31a24215ddd8e04dac837fb699009d35590705be8443dc32d2cab1'

def adapt_bootstrap(entry):
    """Use the profile as staging parent; retain every upstream ACL check."""
    source=entry.read_text(encoding='utf-8')
    if source.count('%LOCALAPPDATA%')!=1 or source.count('$env:LOCALAPPDATA')!=3:
        raise RuntimeError('Cambió el contrato de almacenamiento del bootstrap de Gentle.')
    source=source.replace('%LOCALAPPDATA%','%USERPROFILE%').replace('$env:LOCALAPPDATA','$env:USERPROFILE')
    with entry.open('w',encoding='utf-8',newline='\r\n') as output:output.write(source)

def adapt(entry):
    source=entry.read_text(encoding='utf-8')
    start='return runStandardInstall(request, {'
    end='\t\t\tlog,\n\t\t});\n\t\t},'
    if source.count(start)!=1 or source.count(end)!=1:
        raise RuntimeError('El contrato del instalador oficial cambió; revisa el adaptador.')
    source=source.replace('runInstall: async (request, log) => {', 'runInstall: async (request, log, ariseChannel) => {')
    source=source.replace(start,'const ariseResult = await runStandardInstall(request, {')
    source=source.replace(end,'\t\t\tlog,\n\t\t\t});\n\t\t\tawait reportToArise(ariseResult, ariseChannel, { platform, env, run, fs });\n\t\t\treturn ariseResult;\n\t\t},')
    source=source.replace('import { spawn as spawnChild }', 'import { reportToArise } from "./arise-result.mjs";\nimport { spawn as spawnChild }',1)
    entry.write_text(source,encoding='utf-8')
    server=entry.parent.parent/'scripts/installer-server.mjs'
    code=server.read_text(encoding='utf-8')
    needle='runInstall(request, record)'
    if code.count(needle)!=1:raise RuntimeError('Cambió el contrato de canal del instalador.')
    server.write_text(code.replace(needle,'runInstall(request, record, current.channel)'),encoding='utf-8')

def prepare(destination):
    destination=Path(destination)
    with tempfile.TemporaryDirectory() as temporary:
        archive=Path(temporary)/'installer.zip'
        with urllib.request.urlopen(URL,timeout=60) as response,archive.open('wb') as output:
            shutil.copyfileobj(response,output)
        if hashlib.sha256(archive.read_bytes()).hexdigest()!=SHA256:
            raise RuntimeError('El instalador de Gentle no coincide con el SHA-256 publicado.')
        extracted=Path(temporary)/'extracted';safe_extract(archive,extracted)
        source=extracted/'Gentle Shell Installer/installer'
        if not (source/'scripts/bootstrap.cmd').is_file():raise RuntimeError('ZIP oficial incompleto.')
        adapt(source/'bin/gentle-shell-install.mjs')
        adapt_bootstrap(source/'scripts/bootstrap.cmd')
        shutil.copy2(Path(__file__).resolve().parents[1]/'arise_app/resources/arise-result.mjs',source/'bin/arise-result.mjs')
        shutil.copytree(source,destination,dirs_exist_ok=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--destination',required=True)
    prepare(parser.parse_args().destination)
