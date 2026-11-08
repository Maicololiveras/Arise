"""ARISE-owned, relocatable Gentle runtime; never modify a global installation."""
import json
import os
from pathlib import Path

KEYS = ('pi_command', 'gentle_path', 'gentle_agent_home', 'gentle_bundle_root', 'gentle_channel', 'engram_bin')


def enabled(config):
    return config.get('engine_mode', 'bundled') == 'bundled'


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')
    os.replace(temporary, path)


def prepare(runtime, bundle, manifest):
    """Validate before adoption; retain the previous engine selection for rollback."""
    if manifest.get('owned_engine') != 1 or not enabled(runtime.storage.config):
        return {}
    bundle = Path(bundle).resolve()
    config = runtime.storage.config
    def artifact(value):
        if not isinstance(value, str) or not value.startswith('@bundle/'):
            raise RuntimeError('El motor integrado contiene una ruta inválida.')
        target = (bundle / value[8:]).resolve()
        if not target.is_relative_to(bundle):
            raise RuntimeError('Una ruta del motor integrado sale del paquete.')
        return target
    command = [str(artifact(v)) for v in manifest['pi_command']]
    gentle = artifact(manifest['gentle_path'])
    if len(command) != 2 or not all(Path(p).is_file() for p in command):
        raise RuntimeError('Falta Node o Pi en ARISE. Reinstala el paquete completo; no necesitas instalar Gentle por separado.')
    package = json.loads((gentle/'package.json').read_text(encoding='utf-8'))
    if package.get('name') != 'gentle-pi' or package.get('version') != manifest['versions']['gentle'] or not (gentle/'extensions').is_dir():
        raise RuntimeError('Gentle integrado no coincide con el manifiesto de ARISE.')
    from .discovery import installed_pi_version
    from .gentle_compat import require_compatible_pi
    version = installed_pi_version(command)
    require_compatible_pi(package, version)
    if version != manifest['versions']['pi']:
        raise RuntimeError('Pi integrado no coincide con el manifiesto de ARISE.')
    memory = artifact(manifest['memory_package'])
    meta = json.loads((memory/'package.json').read_text(encoding='utf-8'))
    if meta.get('name') != 'gentle-engram' or meta.get('engram', {}).get('startupPolicy') != 1:
        raise RuntimeError('El complemento de memoria integrado está incompleto.')
    binary = artifact(manifest['engram_bin'])
    if not binary.is_file(): raise RuntimeError('Falta Engram integrado. Reinstala ARISE.')
    base = runtime.storage.root/'engine'
    home = base/'agent'
    # Do not adopt a linked/replaced home into an unrelated location.
    for directory in (base, home, base/'home', base/'gentle-ai', base/'memory'):
        if directory.is_symlink() or (directory.exists() and directory.resolve() != directory.absolute()):
            raise RuntimeError('El entorno integrado debe estar dentro de los datos de ARISE, sin enlaces externos.')
        directory.mkdir(parents=True, exist_ok=True)
    settings = home/'settings.json'
    state_path = base/'runtime.json'
    previous = json.loads(state_path.read_text()) if state_path.exists() else {}
    value = json.loads(settings.read_text(encoding='utf-8-sig')) if settings.exists() else {'theme':'gentleman'}
    packages = value.get('packages', [])
    if not isinstance(packages, list): raise RuntimeError('La lista de paquetes del agente integrado es inválida.')
    packages = [p for p in packages if p != previous.get('memory_package') and p != previous.get('gentle_package')]
    declaration = {'source': str(gentle), 'extensions': []}
    if declaration not in packages: packages.append(declaration)
    if str(memory) not in packages: packages.append(str(memory))
    value['packages'] = packages
    atomic_json(settings, value)
    marker = base/'selection-backup.json'
    if not marker.exists():
        atomic_json(marker, {k:config.get(k) for k in KEYS})
    desired = {'pi_command':command, 'gentle_path':str(gentle), 'gentle_agent_home':str(home),
               'gentle_bundle_root':'', 'gentle_channel':'release', 'engine_mode':'bundled',
               'owned_engine_root':str(base)}
    selected_binary = Path(config.get('engram_bin') or '/missing').resolve()
    if not selected_binary.is_file() or not selected_binary.is_relative_to(runtime.storage.root.resolve()) or str(selected_binary) == previous.get('engram_bin'):
        desired['engram_bin'] = str(binary)
    atomic_json(state_path, {'memory_package':str(memory), 'gentle_package':declaration, 'engram_bin':str(binary), 'versions':manifest['versions']})
    return {k:v for k,v in desired.items() if config.get(k) != v}


def environment(source, config):
    """Separate writable state and inherited overrides; keep Git identity; use a session-owned private memory server."""
    if not enabled(config) or not config.get('owned_engine_root'):
        return dict(source)
    base = Path(config['owned_engine_root'])
    home = base/'home'
    env = dict(source)
    real_home = source.get('USERPROFILE') or source.get('HOME') or str(Path.home())
    # A parent terminal's development overrides and child permission state do not belong to ARISE.
    for key in list(env):
        if key.startswith(('GENTLE_', 'ARISE_GENTLE_')) or key in ('PI_CODING_AGENT_DIR', 'NODE_OPTIONS', 'NODE_PATH'):
            env.pop(key, None)
    env.update(HOME=str(home), USERPROFILE=str(home),
               PI_CODING_AGENT_DIR=config['gentle_agent_home'], GENTLE_PI_AGENT_HOME=config['gentle_agent_home'],
               GENTLE_PI_CONFIG_HOME=str(base/'gentle-ai'), GENTLE_SHELL_USER_PI_HOME=config['gentle_agent_home'],
               GENTLE_SHELL_NO_AUTO_SETUP='1', GENTLE_PI_SKIP_GENTLE_AI_INSTALL='1',
               ARISE_GENTLE_ROOT=config['gentle_path'], ARISE_GENTLE_HOME=config['gentle_agent_home'],
               GENTLE_SHELL_INTERACTIVE_HOST='1', ARISE_GENTLE_OWNED='1')
    folders = {'XDG_CONFIG_HOME':home/'.config', 'XDG_DATA_HOME':home/'.local/share',
               'XDG_CACHE_HOME':home/'.cache', 'XDG_STATE_HOME':home/'.local/state',
               'TMPDIR':home/'.cache/tmp'}
    if os.name == 'nt':
        folders.update(APPDATA=home/'AppData/Roaming', LOCALAPPDATA=home/'AppData/Local',
                       TEMP=home/'.cache/tmp', TMP=home/'.cache/tmp')
    for key,path in folders.items():
        path.mkdir(parents=True, exist_ok=True);env[key]=str(path)
    git = Path(real_home)/'.gitconfig'
    if git.is_file(): env.setdefault('GIT_CONFIG_GLOBAL',str(git))
    # Never open/migrate the user's global database as a side effect of engine setup.
    for key in ('ENGRAM_URL', 'ENGRAM_PORT', 'ENGRAM_HTTP_TOKEN'):
        env.pop(key, None)
    env['ENGRAM_DATA_DIR'] = str(base/'memory')
    env['ENGRAM_SERVER_MODE'] = 'session-owned'
    node = str(Path(config['pi_command'][0]).parent)
    paths = [v for k,v in env.items() if k.upper() == 'PATH']
    for key in list(env):
        if key.upper() == 'PATH':env.pop(key)
    env['PATH'] = node + os.pathsep + (paths[0] if paths else '')
    return env
