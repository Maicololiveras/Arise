"""Run in a private Windows checkout. Only out/ is eligible for publication."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib
import zipfile

TOOLS = {'forge': 'forge-mcp', 'screenview': 'screenview-mcp', 'inputcontrol': 'inputcontrol-mcp'}

def run(*args):
    subprocess.run(args, check=True)

def build(tool):
    name = TOOLS[tool]
    out = Path('out'); out.mkdir(exist_ok=True)
    if tool == 'forge':
        version = json.loads(Path('package.json').read_text())['version']
        run('bun', 'build', './mcp/forge-runtime-mcp-node.ts', '--compile', '--minify', '--bytecode', '--outfile', f'build-public/{name}.exe')
        payload = Path('build-public')
    else:
        version = tomllib.loads(Path('pyproject.toml').read_text())['project']['version']
        module = name.replace('-', '_')
        Path('public_entry.py').write_text(f'from {module}.server import main\nif __name__ == "__main__": main()\n')
        run(sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir', '--name', name,
            '--collect-all', module, '--collect-submodules', 'mcp.server', '--collect-data', 'mcp', '--copy-metadata', 'mcp', '--collect-all', 'pynput' if tool == 'inputcontrol' else 'mss',
            '--hidden-import', 'win32timezone',
            *(['--collect-submodules', 'winrt'] if tool == 'screenview' else []), 'public_entry.py')
        payload = Path('dist') / name
        # collect-all may copy project source as data. Never release those files.
        for p in list(payload.rglob('*')):
            if p.is_file() and p.suffix.lower() in ('.py', '.pyi', '.pyx', '.map', '.ts'):
                p.unlink()
    shutil.copyfile('LICENSE', payload / 'LICENSE.txt')
    notices = []
    if tool == 'forge':
        for p in sorted(Path('node_modules').rglob('*')):
            if p.is_file() and p.name.lower().startswith(('license', 'copying', 'notice')):
                notices.append(str(p) + '\n' + p.read_text(errors='replace'))
    else:
        for d in importlib.metadata.distributions():
            notices.append(f"{d.metadata['Name']} {d.version}: {d.metadata.get('License', '')}")
            for f in d.files or []:
                if Path(str(f)).name.lower().startswith(('license', 'copying', 'notice')):
                    p = Path(d.locate_file(f))
                    if p.is_file(): notices.append(str(f) + '\n' + p.read_text(errors='replace'))
    (payload / 'THIRD-PARTY-NOTICES.txt').write_text('\n\n'.join(notices), encoding='utf-8')
    run(sys.executable, os.environ['DISTRIBUTION_SCRIPTS'] + '/smoke.py', str((payload / (name + '.exe')).resolve()))
    sha = os.environ['GITHUB_SHA']
    tag = f'herramientas-{tool}-v{version}-{sha[:12]}'
    archive = out / f'{name}-windows-x64.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in sorted(payload.rglob('*')):
            if p.is_file():
                if p.suffix.lower() in ('.py', '.pyi', '.ts', '.map'):
                    raise RuntimeError('Source file in release payload')
                z.write(p, p.relative_to(payload))
    manifest = {'schema': 1, 'tool': tool, 'version': version, 'tag': tag, 'platform': 'windows-x64',
        'entry': name + '.exe', 'sha256': hashlib.file_digest(archive.open('rb'), 'sha256').hexdigest(),
        'size': archive.stat().st_size, 'url': f'https://github.com/Maicololiveras/Arise/releases/download/{tag}/{archive.name}'}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    (out / (archive.name + '.sha256')).write_text(manifest['sha256'] + '  ' + archive.name + '\n')
    print(json.dumps(manifest))

if __name__ == '__main__': build(sys.argv[1])
