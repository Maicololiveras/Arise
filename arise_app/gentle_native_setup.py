"""Explicit native TUI alternative; never bypass the installed supervisor.

Native Windows 4.3.1 sanitizes ARISE_* out of its environment. Installation and
CLI launch can be verified, but that is not authority to adopt its private Node
as ARISE's RPC engine. Preserve the working engine and report this limitation.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

MIN_VERSION = (4, 3, 1)


def native_version(binary, env):
    result = subprocess.run([str(binary), '--version'], env=env, capture_output=True,
                            text=True, timeout=30, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    match = re.search(r'(?i)\bgentle[- ]ai\s+(?:version\s+)?v?(\d+)\.(\d+)\.(\d+)(?![\d.-])', result.stdout)
    if result.returncode or not match or tuple(map(int, match.groups())) < MIN_VERSION:
        raise RuntimeError('La TUI requiere Gentle AI estable 4.3.1 o superior. Actualiza el binario; no se usará automáticamente un dev override antiguo.')
    return '.'.join(match.groups())


def resolve_binary(runtime, env, selected=None):
    if selected:
        binary = Path(selected)
        if not binary.is_absolute() or binary.suffix.lower() != '.exe' or not binary.is_file():
            raise ValueError('Selecciona un archivo gentle-ai.exe existente con ruta absoluta.')
        return binary.resolve()
    from .bundle import application_root
    bundle = application_root() / 'bundle'
    bundled_package = bundle/'node/node_modules/gentle-pi'
    package = bundled_package if (bundled_package/'runtime/gentle-ai-binary.mjs').is_file() else Path(runtime.storage.config.get('gentle_path') or bundled_package)
    node = bundle/'node/node.exe'
    if not node.is_file():
        from .windows_prerequisites import find_native
        node = find_native('node.exe', env)
    if not node or not (package/'runtime/gentle-ai-binary.mjs').is_file():
        raise RuntimeError('Falta el binario integrado. Usa el nuevo ZIP de QA o selecciona tu gentle-ai.exe instalado mediante Go.')
    helper = Path(__file__).parent/'resources/resolve-gentle-native.mjs'
    result = subprocess.run([str(node), str(helper), str(package)], env=env, capture_output=True,
                            text=True, timeout=45, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise RuntimeError('El verificador oficial rechazó el binario integrado. Repara Gentle o selecciona explícitamente tu gentle-ai.exe; no se desactivó la verificación.')
    binary = Path(json.loads(result.stdout)['path'])
    if not binary.is_absolute() or not binary.is_file(): raise RuntimeError('El binario verificado no existe.')
    return binary


def inspect_native_target(target, env):
    """Verify through the owned launcher, not by executing private node directly."""
    target = Path(target)
    required = [target/'manifest.json', target/'selection.json', target/'supervisor.exe',
                target/'bin/gentle-shell.cmd', target/'prefix/node_modules/gentle-pi/package.json']
    if not all(p.is_file() for p in required):
        raise RuntimeError('La TUI no dejó una instalación completa en '+str(target)+'. Puede haberse cancelado o elegido otro destino. No se cambió el motor de ARISE.')
    manifest_file=required[0]
    if manifest_file.stat().st_size > 4096: raise RuntimeError('Manifiesto nativo inválido.')
    manifest=json.loads(manifest_file.read_text(encoding='utf-8'))
    # Use only the fixed path, never a command or path supplied by the manifest.
    supervisor=target/'supervisor.exe'
    if supervisor.stat().st_size > 256*1024*1024: raise RuntimeError('Supervisor nativo demasiado grande.')
    expected=manifest.get('SupervisorSHA')
    if not isinstance(expected,str) or hashlib.sha256(supervisor.read_bytes()).hexdigest()!=expected:
        raise RuntimeError('El supervisor no coincide con su manifiesto. No se ejecutó.')
    result=subprocess.run([str(supervisor),'shell','launch',str(target),'gentle-shell','--version'],
                          env=env,capture_output=True,text=True,timeout=180,
                          creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:
        raise RuntimeError('El supervisor de Gentle rechazó la apertura de Shell. Revisa la instalación desde Gentle AI; ARISE no ejecutará el Node privado para evitar ese rechazo.')
    match=re.search(r'(?i)gentle[- ]shell\s+(\d+\.\d+\.\d+(?:-[^\s]+)?)',result.stdout)
    if not match:
        raise RuntimeError('El lanzador terminó sin identificar Gentle Shell. No se confirmó la instalación.')
    return {'installed':True,'launcher_verified':True,'connected':False,'target':str(target),'shell_version':match.group(1)}


def install_native_tui(runtime, selected=None, timeout=4500):
    if os.name != 'nt': raise RuntimeError('Esta alternativa de QA requiere Windows 11 x64.')
    from .gentle_setup import LOCK
    if not LOCK.acquire(blocking=False): raise RuntimeError('El instalador de Gentle ya está abierto.')
    process=None
    diagnostic=None
    try:
        with runtime.transition_lock:
            if runtime.busy: raise RuntimeError('Detén la tarea activa antes de abrir el instalador.')
        from .windows_prerequisites import refresh_path
        env=refresh_path(os.environ)
        # Never disclose the desktop bridge or provider credentials to the TUI.
        for key in list(env):
            if key.startswith('ARISE_') or key.endswith(('_API_KEY','_ACCESS_TOKEN')):
                env.pop(key)
        binary=resolve_binary(runtime,env,selected)
        version=native_version(binary,env)
        target=Path(env['LOCALAPPDATA'])/'gentle-shell/install'
        manifest=target/'manifest.json'
        before=manifest.read_bytes() if manifest.is_file() and manifest.stat().st_size<=4096 else None
        import tempfile
        jobs=runtime.storage.root/'installers'; jobs.mkdir(parents=True,exist_ok=True)
        job=Path(tempfile.mkdtemp(prefix='gentle-native-',dir=jobs))
        diagnostic=job/'result.json'
        evidence={'method':'native-tui','binary':str(binary),'version':version,'target':str(target),'status':'opened','connected':False}
        diagnostic.write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
        runtime.emit('notice',{'text':f'Se abrirá Gentle AI {version} en una consola. En su TUI selecciona Gentle Shell, revisa destino y plan, y confirma allí. Al terminar sal de Gentle AI. Tu motor actual de ARISE se conserva.'})
        # No shell command construction, hidden console, redirected stdin or auto-confirm.
        process=subprocess.Popen([str(binary)],cwd=str(binary.parent),env=env,
                                 creationflags=subprocess.CREATE_NEW_CONSOLE)
        deadline=time.monotonic()+timeout
        while process.poll() is None:
            if time.monotonic()>=deadline:
                raise RuntimeError('Gentle AI continúa abierto. Termina o cancela en su consola antes de volver a intentar; no se forzó el cierre.')
            time.sleep(.5)
        if process.returncode:
            raise RuntimeError(f'Gentle AI terminó con código {process.returncode}. Revisa su consola. No se cambió el motor de ARISE.')
        report=inspect_native_target(target,env)
        after=manifest.read_bytes() if manifest.is_file() else None
        report.update(installed=before!=after, reused=before is not None and before==after, diagnostic=str(diagnostic))
        evidence.update(report,status='launcher-verified',exit_code=process.returncode)
        diagnostic.write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
        runtime.emit('notice',{'text':'Instalación nativa y lanzador de Gentle Shell verificados. No se adoptó como motor de ARISE: el supervisor nativo no transmite el contexto de permisos/conexión de ARISE. Usa la instalación habitual para integrar ARISE; esta alternativa permite probar la instalación y Shell independiente.'})
        return report
    except Exception as error:
        if diagnostic is not None:
            evidence.update(status='not-confirmed',error=str(error)[:1500])
            diagnostic.write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
        raise
    finally:
        if process is not None and process.poll() is None:
            # Keep mutual exclusion until the user's still-open installer actually exits.
            import threading
            def release_after_exit():
                try: process.wait()
                finally: LOCK.release()
            threading.Thread(target=release_after_exit,daemon=True).start()
        else: LOCK.release()
