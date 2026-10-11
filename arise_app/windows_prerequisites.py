"""Prepare Windows dependencies before starting the official Gentle wizard."""
import os
import base64
import shutil
from pathlib import Path
import re
import subprocess
from .diagnostics import checked_run

NODE_MIN = (24, 3, 0)  # Official Windows bootstrap floor, stricter than package engines.
GO_MIN = (1, 25, 10)
PNPM_VERSION = '11.1.1'
NPM_VERSION = '11.10.0'
INSTALL_IDS = {'Git': 'Git.Git', 'Go': 'GoLang.Go'}


def refresh_path(env, first=()):
    """Read fresh registry PATH without changing the user's environment or profiles."""
    entries = [str(p) for p in first]
    entries.extend(env.get('PATH', '').split(os.pathsep))
    if os.name == 'nt':
        import winreg
        for hive, key in ((winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment'),
                          (winreg.HKEY_CURRENT_USER, r'Environment')):
            try:
                with winreg.OpenKey(hive, key) as handle:
                    entries.extend(os.path.expandvars(winreg.QueryValueEx(handle, 'Path')[0]).split(os.pathsep))
            except OSError:
                pass
    result = dict(env)
    for canonical in ('SystemRoot', 'ProgramFiles', 'ProgramFiles(x86)', 'ProgramW6432', 'LOCALAPPDATA'):
        for key, value in env.items():
            if key.upper() == canonical.upper():
                result[canonical] = value
                break
    for key in list(result):
        if key.upper() == 'PATH':
            del result[key]
    result['PATH'] = os.pathsep.join(dict.fromkeys(p for p in entries if p and Path(p).is_absolute()))
    return result


def probe(command, env, cwd):
    try:
        result = subprocess.run([str(p) for p in command], env=env, cwd=str(cwd),
                                capture_output=True, text=True, timeout=30,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        return result.stdout.strip() if result.returncode == 0 else ''
    except (OSError, subprocess.TimeoutExpired):
        return ''


def version(output, pattern):
    found = re.fullmatch(pattern, output)
    return tuple(map(int, found.groups()[:3])) if found else None


def find_native(name, env, extra=()):
    # Explicit .exe only; never execute cmd/bat wrappers or a cwd-resolved command.
    for directory in (*extra, *env.get('PATH', '').split(os.pathsep)):
        if directory and Path(directory).is_absolute():
            candidate = Path(directory) / name
            if candidate.is_file():
                return candidate
    return None


def known_dirs(env, tool):
    bases = [Path(env[key]) for key in ('ProgramW6432', 'ProgramFiles', 'ProgramFiles(x86)', 'LOCALAPPDATA') if env.get(key)]
    if tool == 'Git':
        return [p / suffix for p in bases for suffix in ('Git/cmd', 'Programs/Git/cmd')]
    return [p / 'Go/bin' for p in bases]


def find_git(env, cwd):
    for directory in [*env.get('PATH', '').split(os.pathsep), *known_dirs(env, 'Git')]:
        git = find_native('git.exe', {}, [directory])
        if not git or not re.fullmatch(r'git version \d+\.\d+\.\d+(?:\.windows\.\d+)?', probe([git, '--version'], env, cwd)):
            continue
        # Git for Windows' native Bash, not the System32 WSL launcher.
        for bash in (git.parent.parent / 'bin/bash.exe', git.parent.parent / 'usr/bin/bash.exe'):
            if bash.is_file() and 'GNU bash' in probe([bash, '--version'], env, cwd):
                return git, bash
    return None


def find_go(env, cwd):
    for directory in [*env.get('PATH', '').split(os.pathsep), *known_dirs(env, 'Go')]:
        go = find_native('go.exe', {}, [directory])
        value = version(probe([go, 'version'], env, cwd), r'go version go(\d+)\.(\d+)\.(\d+) windows/\S+') if go else None
        if value and value >= GO_MIN:
            return go
    return None


def install_native(tool, env, cwd, notify):
    winget = find_native('winget.exe', env, [Path(env.get('LOCALAPPDATA', '')) / 'Microsoft/WindowsApps'])
    package = INSTALL_IDS[tool]
    if not winget:
        raise RuntimeError(f'Falta {tool}. Instala App Installer/WinGet o {tool} desde su sitio oficial y reintenta. '
                           f'Comando: winget install --id {package} --exact --source winget')
    notify(f'Instalando {tool} antes de Gentle Shell. Windows puede pedir autorización.')
    try:
        checked_run([str(winget), 'install', '--id', package, '--exact', '--source', 'winget',
                     '--accept-package-agreements', '--accept-source-agreements', '--disable-interactivity'],
                    f'Instalación de {tool}', env=env, cwd=str(cwd), timeout=1200,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except RuntimeError as error:
        raise RuntimeError(f'{error} Gentle Shell no se inició. Reintenta o ejecuta '
                           f'winget install --id {package} --exact --source winget') from None


def prepare_manager_directory():
    """Own one private directory; never change permissions on an existing tree."""
    from .gentle_setup import STAGE_SCRIPT
    directory = Path(os.environ['USERPROFILE']).resolve() / 'ARISE-Gentle-Prerequisites'
    created = False
    try:
        directory.mkdir()
        created = True
    except FileExistsError:
        pass
    script = STAGE_SCRIPT.replace("'^ARISE-Gentle-Setup-[a-f0-9]{32}$'", "'^ARISE-Gentle-Prerequisites$'")
    start = script.index("if ([IO.Directory]::GetFileSystemEntries")
    end = script.index('$actual =')
    if not created:
        script = script[:start] + '$me = [Security.Principal.WindowsIdentity]::GetCurrent().User\n' + script[end:]
    env = dict(os.environ, ARISE_GENTLE_STAGE=str(directory))
    powershell = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    checked_run([str(powershell), '-NoLogo', '-NoProfile', '-NonInteractive', '-EncodedCommand',
                 base64.b64encode(script.encode('utf-16-le')).decode('ascii')],
                'Verificación de la carpeta privada de dependencias', env=env, timeout=30,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    return directory


def prepare_prerequisites(bundle, root, notify=lambda message: None, env=None):
    """Return a verified child environment; failure never launches Gentle Shell."""
    bundle, root = Path(bundle), Path(root)
    root.mkdir(parents=True, exist_ok=True)
    env = refresh_path(dict(os.environ if env is None else env))
    node = bundle / 'node/node.exe'
    npm = bundle / 'node/node_modules/npm/bin/npm-cli.js'
    node_version = version(probe([node, '--version'], env, root), r'v(\d+)\.(\d+)\.(\d+)')
    if not node_version or node_version < NODE_MIN or not npm.is_file():
        raise RuntimeError('El Node/npm incluido en ARISE falta o no es compatible. Reinstala el ZIP completo actualizado.')
    env = refresh_path(env, [node.parent])
    npm_version = version(probe([node, npm, '--version'], env, root), r'(\d+)\.(\d+)\.(\d+)')
    if not npm_version:
        raise RuntimeError('El npm incluido no funciona. Reinstala el ZIP completo de ARISE.')
    notify('Node y npm integrados verificados.')
    tar = Path(env.get('SystemRoot', r'C:\Windows')) / 'System32/tar.exe'
    if not tar.is_file() or 'tar' not in probe([tar, '--version'], env, root).lower():
        raise RuntimeError('Falta el tar.exe de Windows o no funciona. Actualiza/repara Windows antes de instalar Gentle Shell.')
    for tool, detect in (('Git', find_git), ('Go', find_go)):
        found = detect(env, root)
        if not found:
            install_native(tool, env, root, notify)
            env = refresh_path(env)
            found = detect(env, root)
        if not found:
            raise RuntimeError(f'{tool} sigue ausente o incompatible tras instalarlo. Gentle Shell no se inició; revisa PATH y reintenta.')
        if tool == 'Git':
            git, bash = found
            env = refresh_path(env, [git.parent, bash.parent])
        else:
            env = refresh_path(env, [found.parent])
        notify(f'{tool} verificado.')
    # A private prefix preserves any global package-manager version the user owns.
    managers = prepare_manager_directory()
    # npm's shim prefers its sibling Node; keep that binary in the private ACL tree.
    shutil.copyfile(node, managers / 'node.exe')
    pnpm = managers / 'node_modules/pnpm/bin/pnpm.cjs'
    if not pnpm.is_file():
        pnpm = managers / 'node_modules/pnpm/bin/pnpm.mjs'
    private_npm = managers / 'node_modules/npm/bin/npm-cli.js'
    def managers_ready():
        return (probe([node, pnpm, '--version'], env, root) == PNPM_VERSION
                and probe([node, private_npm, '--version'], env, root) == NPM_VERSION
                and (managers / 'pnpm.cmd').is_file() and (managers / 'npm.cmd').is_file())
    if not managers_ready():
        notify('Preparando pnpm y npm para Gentle Shell en la carpeta de ARISE…')
        checked_run([str(node), str(npm), 'install', '--global', '--prefix', str(managers),
                     '--registry=https://registry.npmjs.org', '--ignore-scripts', '--no-audit', '--no-fund',
                     f'pnpm@{PNPM_VERSION}', f'npm@{NPM_VERSION}'],
                    'Preparación de pnpm/npm', env=env, cwd=str(root), timeout=600,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        pnpm = managers / 'node_modules/pnpm/bin/pnpm.mjs'
        if not managers_ready():
            raise RuntimeError('pnpm/npm no superaron la verificación. Gentle Shell no se inició; revisa la conexión y reintenta.')
    env = refresh_path(env, [node.parent, managers])
    notify('Dependencias listas: Node, npm, pnpm, Git/Bash, Go y tar. Abriendo Gentle Shell…')
    return env
