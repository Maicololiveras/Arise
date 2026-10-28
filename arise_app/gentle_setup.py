"""Run the official interactive installer and adopt only its verified result."""
import json
import base64
import os
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from pathlib import Path
from .bundle import application_root

LOCK=threading.Lock()

# Fixed PowerShell source. Paths are environment data, never interpolated code.
# Only the new, empty directory created by this invocation is modified.
STAGE_SCRIPT=r'''
$ErrorActionPreference = 'Stop'
if ($ExecutionContext.SessionState.LanguageMode -ne 'FullLanguage') { throw 'policy' }
$root = [IO.Path]::GetFullPath($env:ARISE_GENTLE_STAGE)
$profile = [IO.Path]::GetFullPath($env:USERPROFILE)
if ($root.StartsWith('\\') -or [IO.Path]::GetDirectoryName($root) -ne $profile -or
    [IO.Path]::GetFileName($root) -cnotmatch '^ARISE-Gentle-Setup-[a-f0-9]{32}$') { throw 'stage-path' }
foreach ($path in @($profile, $root)) {
    $item = Get-Item -LiteralPath $path -Force
    if (-not $item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'stage-reparse' }
}
if ([IO.Directory]::GetFileSystemEntries($root).Length -ne 0) { throw 'stage-not-empty' }
$me = [Security.Principal.WindowsIdentity]::GetCurrent().User
$acl = New-Object Security.AccessControl.DirectorySecurity
$acl.SetOwner($me)
$acl.SetAccessRuleProtection($true,$false)
foreach ($sid in @($me.Value,'S-1-5-18','S-1-5-32-544')) {
    $identity = New-Object Security.Principal.SecurityIdentifier($sid)
    $rule = New-Object Security.AccessControl.FileSystemAccessRule($identity,'FullControl','ContainerInherit,ObjectInherit','None','Allow')
    $acl.AddAccessRule($rule)
}
[IO.Directory]::SetAccessControl($root,$acl)
$actual = [IO.Directory]::GetAccessControl($root)
if ($actual.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne $me.Value -or
    -not $actual.AreAccessRulesProtected) { throw 'stage-owner-or-acl' }
foreach ($rule in $actual.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])) {
    if ($rule.AccessControlType -ne 'Allow' -or @($me.Value,'S-1-5-18','S-1-5-32-544') -notcontains $rule.IdentityReference.Value) { throw 'stage-ace' }
}
'''

def prepare_installer_stage():
    profile=Path(os.environ['USERPROFILE'])
    if not profile.is_absolute():raise RuntimeError('La ruta del perfil de Windows no es absoluta.')
    stage=profile/('ARISE-Gentle-Setup-'+uuid.uuid4().hex)
    stage.mkdir()  # Exclusive creation: never repair/reuse an existing directory.
    env=os.environ.copy();env['ARISE_GENTLE_STAGE']=str(stage)
    powershell=str(Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe')
    encoded=base64.b64encode(STAGE_SCRIPT.encode('utf-16-le')).decode('ascii')
    try:
        result=subprocess.run([powershell,'-NoLogo','-NoProfile','-NonInteractive','-EncodedCommand',encoded],
            env=env,capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:
            raise RuntimeError('No se pudo preparar una carpeta privada para Gentle. No se modificaron los permisos del perfil ni de AppData.')
    except Exception:
        # Remove only this empty directory; never recurse through staging content.
        try:stage.rmdir()
        except OSError:pass
        raise
    return stage,env

def wait_for_installer(process, result_file, log_file, timeout):
    deadline=time.monotonic()+timeout
    while not result_file.is_file():
        code=process.poll()
        if code is not None:
            # The result reporter writes atomically; allow its final rename.
            if result_file.is_file():break
            tail=''
            try:
                with log_file.open('rb') as stream:
                    stream.seek(0,2);size=stream.tell();stream.seek(max(0,size-8192))
                    tail=stream.read().decode('utf-8',errors='replace')
            except OSError:pass
            reason=' Los permisos de la carpeta temporal fueron rechazados (acl-mask).' if 'acl-mask' in tail else ''
            if 'process-failed (entry-storage)' in tail:
                reason = (' Falló la comprobación del archivo de entrada del pnpm existente '
                          '(entry-storage), antes del asistente. El registro no distingue '
                          'archivo ausente, permisos o política de PowerShell; no se modificó pnpm.')
            for diagnostic_code, detail in {
                'target-io': 'PowerShell no pudo leer los metadatos del almacenamiento.',
                'target-access-denied': 'Windows denegó la lectura del almacenamiento.',
                'target-path-too-long': 'La ruta excede el límite admitido por la comprobación de Windows.',
                'target-not-found': 'La comprobación no encontró el archivo o una carpeta de su ruta.',
                'target-process-timeout': 'La validación de PowerShell superó los 15 segundos.',
                'target-process-start': 'No se pudo iniciar el proceso de validación de PowerShell.',
                'target-process-exit': 'PowerShell terminó con error antes de devolver evidencia válida.',
            }.items():
                if 'Reason: ' + diagnostic_code + ' (' in tail:
                    reason = ' ' + detail
                    break
            raise RuntimeError(f'El instalador de Gentle terminó (código {code}) sin confirmar la instalación.{reason} Diagnóstico: {log_file}')
        if time.monotonic()>=deadline:
            raise RuntimeError(f'El instalador sigue abierto sin confirmar. Revisa su ventana antes de reintentar. Diagnóstico: {log_file}')
        time.sleep(.5)

def validate_result(result, node):
    if not isinstance(result,dict): raise ValueError('Resultado del detector de Gentle inválido.')
    if result.get('status')!='ready':
        if result.get('reason')=='install-shell-main':
            raise RuntimeError('Gentle superó la preparación, pero falló al instalar Shell desde main. Revisa el instalador web; puedes reintentar main o elegir estable explícitamente. ARISE no adoptó una instalación incompleta.')
        raise RuntimeError('Gentle no completó la instalación: '+str(result.get('reason','sin resultado'))[:200])
    if result.get('channel') not in ('release','main'):raise ValueError('Canal de Gentle inválido.')
    roots=[Path(result[key]) for key in ('pi_root','gentle_root','agent_home')]
    if not all(path.is_absolute() and path.is_dir() for path in roots):raise ValueError('Faltan carpetas de la instalación de Gentle.')
    pi,gentle,home=roots
    metadata=json.loads((pi/'package.json').read_text(encoding='utf-8'))
    shell=json.loads((gentle/'package.json').read_text(encoding='utf-8'))
    if metadata.get('name')!='@earendil-works/pi-coding-agent' or shell.get('name') not in ('gentle-pi','gentle-shell'):
        raise ValueError('Los paquetes instalados no corresponden a Pi/Gentle.')
    cli=(pi/metadata['bin']['pi']).resolve()
    if not cli.is_relative_to(pi.resolve()) or not cli.is_file() or not (gentle/'extensions').is_dir() or not Path(node).is_file():
        raise ValueError('La instalación de Pi/Gentle está incompleta.')
    from .gentle_compat import require_compatible_pi
    require_compatible_pi(shell, metadata.get('version'))
    prefix=result.get('bundle_root', '')
    if prefix and (not Path(prefix).is_absolute() or not Path(prefix).is_dir()): raise ValueError('Entorno privado de Gentle inválido.')
    return {'gentle_bundle_root':prefix, 'pi_command':[str(node),str(cli)],'gentle_path':str(gentle),'gentle_agent_home':str(home),'gentle_channel':result['channel']}

def adopt_gentle(runtime, changes):
    """Commit an engine selection only after its real RPC commands are available."""
    with runtime.transition_lock:
        if runtime.busy: raise RuntimeError('Detén la tarea activa antes de configurar Gentle.')
        previous={key:runtime.storage.config.get(key,'') for key in changes}
        runtime.disconnect()
        runtime.settings(changes)
        try:
            if not runtime.connect_pi().get('gentleVerified'):
                raise RuntimeError('Pi inició, pero no registró los comandos de Gentle.')
        except Exception:
            runtime.disconnect()
            runtime.settings(previous)
            raise


def install_gentle(runtime, timeout=3600, force_update=False):
    if os.name!='nt':raise RuntimeError('Este instalador de Gentle requiere Windows.')
    if not LOCK.acquire(blocking=False):raise RuntimeError('El instalador de Gentle ya está abierto.')
    try:
        with runtime.transition_lock:
            if runtime.busy:raise RuntimeError('Detén la tarea activa antes de instalar Gentle.')
            runtime.disconnect()
        from .windows_prerequisites import refresh_path
        from .discovery import detect_gentle_installation
        env=refresh_path(os.environ)
        existing=None if force_update else detect_gentle_installation(env, prefix=runtime.storage.config.get("gentle_bundle_root"))
        if existing:
            os.environ['PATH']=env['PATH']
            runtime.emit('notice',{'text':'Gentle existente detectado: '+existing['gentle_path']+'. Verificando su motor y comandos.'})
            adopt_gentle(runtime,existing)
            runtime.emit('notice',{'text':'ARISE usa tu Gentle existente y su carpeta de agente. No fue necesario reinstalarlo.'})
            from .tool_setup import auto_setup
            auto_setup(runtime)
            return {'installed':False,'reused':True,'channel':existing['gentle_channel'],'verified':True}
        bundle=application_root()/'bundle'
        source=bundle/'gentle-installer'
        if not (source/'scripts/bootstrap.cmd').is_file():raise RuntimeError('Usa el ZIP nuevo de ARISE: falta el instalador oficial de Gentle.')
        from .windows_prerequisites import prepare_shell_prerequisites, refresh_path
        env=prepare_shell_prerequisites(bundle,runtime.storage.root/'prerequisites',
            lambda message:runtime.emit('notice',{'text':message}))
        jobs=runtime.storage.root/'installers';jobs.mkdir(exist_ok=True)
        # Keep the job if the UI closes; the installer may still own files in it.
        job=Path(tempfile.mkdtemp(prefix='gentle-',dir=jobs))
        shutil.copytree(source,job,dirs_exist_ok=True)
        runtime.emit('notice',{'text':'Se abrirá el instalador oficial. Elige versión estable o último main y confirma su plan. ARISE verificará el resultado.'})
        result_file=job/'arise-result.json'
        log_file=job/'bootstrap.log'
        command=str(Path(os.environ['SystemRoot'])/'System32/cmd.exe')
        with log_file.open('wb') as log:
            process=subprocess.Popen([command,'/d','/c','bootstrap.cmd'],cwd=str(job/'scripts'),env=env,
                stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            runtime.emit('notice',{'text':f'Gentle preparará su entorno privado y abrirá el asistente. Diagnóstico: {log_file}'})
            wait_for_installer(process,result_file,log_file,timeout)
        result=json.loads(result_file.read_text(encoding='utf-8'))
        changes=validate_result(result,Path(result.get('node') or bundle/'node/node.exe'))
        # Pi starts in this daemon too: inherit installed Git/Go without a restart.
        os.environ['PATH']=refresh_path(env)['PATH']
        adopt_gentle(runtime,changes)
        runtime.emit('notice',{'text':'Gentle '+result['channel']+' instalado y conectado. Sus comandos se verificaron en Pi.'})
        from .tool_setup import auto_setup
        auto_setup(runtime)
        return {'installed':True,'channel':result['channel'],'version':result.get('version'),'verified':True}
    finally:LOCK.release()
