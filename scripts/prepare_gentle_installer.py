"""Bundle the pinned official Windows wizard, with a result-only ARISE adapter."""
import argparse
import hashlib
import json
import re
import shutil
import tempfile
import urllib.request
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from arise_app.downloads import safe_extract

URL='https://github.com/Gentleman-Programming/gentle-shell/releases/download/v4.2.0/gentle-shell-installer-windows.zip'
SHA256='352bf1971c00beb555a97279d59c2ea2946e6b261c446d9b3fe787bd6689a1bb'

def adapt_bootstrap(entry):
    """Use ARISE's private staging parent; retain every upstream ACL check."""
    source=entry.read_text(encoding='utf-8')
    if source.count('%LOCALAPPDATA%')!=1 or source.count('$env:LOCALAPPDATA')!=3:
        raise RuntimeError('Cambió el contrato de almacenamiento del bootstrap de Gentle.')
    source=source.replace('%LOCALAPPDATA%','%ARISE_GENTLE_STAGE%').replace('$env:LOCALAPPDATA','$env:ARISE_GENTLE_STAGE')
    with entry.open('w',encoding='utf-8',newline='\r\n') as output:output.write(source)

def adapt(entry):
    # Wrap the wizard boundary so both standard and bundled installations report.
    source=entry.read_text(encoding='utf-8')
    needle='...wizardHandlers({ platform, arch, env, run, fs }),'
    if source.count(needle)!=1: raise RuntimeError('Cambió el contrato del instalador oficial.')
    context_needle='\treturn {\n\t\tcollectPlan: async (channel) => {'
    if source.count(context_needle)!=1: raise RuntimeError('Cambió el contexto del instalador oficial.')
    source=source.replace(context_needle, '\treturn {\n\t\tariseContext: () => ({ env: wizard.env, pnpmHome: wizard.pnpmHome }),\n\t\tcollectPlan: async (channel) => {')
    source=source.replace(needle, '...withAriseReport(wizardHandlers({ platform, arch, env, run, fs }), { platform, arch, env, run, fs }),')
    source='import { withAriseReport } from "./arise-result.mjs";\n'+source
    # Preserve the executable hashbang as the first line.
    if source.count('#!/usr/bin/env node'):
        source=source.replace('#!/usr/bin/env node\n','');source='#!/usr/bin/env node\n'+source
    entry.write_text(source,encoding='utf-8')


def adapt_windows_storage(entry):
    """Extend only the known pnpm junction layout; keep fail-closed ACL checks."""
    source = entry.read_text(encoding='utf-8')
    pattern = r'const aclCheck = String.raw`.*?`;'
    matches = list(re.finditer(pattern, source, re.S))
    if len(matches) != 1:
        raise RuntimeError('Cambió el contrato de validación Windows de Gentle.')
    script = (Path(__file__).resolve().parents[1] /
              'arise_app/resources/pnpm-storage-check.ps1').read_text(encoding='utf-8')
    match = matches[0]
    source = source[:match.start()] + 'const aclCheck = ' + json.dumps(script) + ';' + source[match.end():]
    # Encode source rather than passing multiline comments/quotes through -Command.
    transport = '"-Command", script'
    if source.count(transport) != 1:
        raise RuntimeError('Cambió el transporte PowerShell del instalador.')
    source = source.replace(transport, '"-EncodedCommand", Buffer.from(script, "utf16le").toString("base64")')
    checks = 'const storageChecks = /^(?:policy|(?:target|parent|ancestor)-(?:reparse|owner|acl-mask))$/;'
    if source.count(checks) != 1:
        raise RuntimeError('Cambió el contrato de errores de almacenamiento.')
    source = source.replace(checks, checks.replace('reparse|owner|acl-mask', 'reparse|owner|acl-mask|io|access-denied|path-too-long|not-found|process-timeout|process-start|process-exit'))
    failure = 'if (result.error || result.status !== 0) throw new Error("Windows prerequisite process failed");'
    if source.count(failure) != 1:
        raise RuntimeError('Cambió el contrato del proceso de validación Windows.')
    replacement = '''if (result.error || result.status !== 0) {
        const error = new Error("Windows prerequisite process failed");
        if (args.includes("-EncodedCommand")) error.check = result.error?.code === "ETIMEDOUT" ? "target-process-timeout" : result.error ? "target-process-start" : "target-process-exit";
        throw error;
    }'''
    source = source.replace(failure, replacement)
    entry.write_text(source, encoding='utf-8')


def prepare(destination):
    destination=Path(destination)
    with tempfile.TemporaryDirectory() as temporary:
        archive=Path(temporary)/'installer.zip'
        with urllib.request.urlopen(URL,timeout=60) as response:
            data=response.read(2_000_001)
        if len(data)>2_000_000: raise RuntimeError('El instalador oficial supera el límite.')
        archive.write_bytes(data)
        if hashlib.sha256(archive.read_bytes()).hexdigest()!=SHA256:
            raise RuntimeError('El instalador de Gentle no coincide con el SHA-256 publicado.')
        extracted=Path(temporary)/'extracted';safe_extract(archive,extracted)
        source=extracted/'Gentle Shell Installer/installer'
        if not (source/'scripts/bootstrap.cmd').is_file():raise RuntimeError('ZIP oficial incompleto.')
        adapt(source/'bin/gentle-shell-install.mjs')
        adapt_windows_storage(source/'scripts/installer-windows.mjs')
        # Keep upstream's ACL checks, SYSTEM-owner support and profile fallback intact.
        shutil.copy2(Path(__file__).resolve().parents[1]/'arise_app/resources/arise-result.mjs',source/'bin/arise-result.mjs')
        shutil.copytree(source,destination,dirs_exist_ok=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--destination',required=True)
    prepare(parser.parse_args().destination)
