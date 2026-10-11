"""Prove real Windows tools/private npm shims work with the shipped Gentle bootstrap."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from arise_app.windows_prerequisites import prepare_prerequisites
from arise_app.gentle_setup import prepare_installer_stage

if os.name != 'nt':
    raise RuntimeError('This smoke check must run on Windows.')
bundle = Path(sys.argv[1]).resolve() / 'bundle'
with tempfile.TemporaryDirectory(prefix='arise-prerequisites-') as temporary:
    root = Path(temporary)
    env = prepare_prerequisites(bundle, root, print)
    # A repeat must reuse all tools and packages without another acquisition.
    if prepare_prerequisites(bundle, root, print) != env:
        raise RuntimeError('Prerequisite environment is not stable across retries.')
    stage, stage_env = prepare_installer_stage()
    env['ARISE_GENTLE_STAGE'] = stage_env['ARISE_GENTLE_STAGE']
    env['ARISE_WINDOWS_ADAPTER'] = str(bundle / 'gentle-installer/scripts/installer-windows.mjs')
    script = '''
        import { pathToFileURL } from 'node:url';
        const { ensureWindowsPnpm } = await import(pathToFileURL(process.env.ARISE_WINDOWS_ADAPTER));
        const result = await ensureWindowsPnpm({tools:process.env.ARISE_GENTLE_STAGE,env:process.env});
        if (result.acquired || !result.command || !result.prefix.length) throw new Error('Prepared pnpm was not reused');
        console.log('Official Windows adapter accepted prepared pnpm');
    '''
    try:
        subprocess.run([str(bundle/'node/node.exe'),'--input-type=module','-e',script],env=env,cwd=root,check=True,timeout=90)
    finally:
        stage.rmdir()
Path('artifacts/gentle-prerequisites.json').write_text(json.dumps({'windows_tools':'passed','private_pnpm':'passed','official_adapter':'passed','repeat':'passed'}),encoding='utf-8')
