"""Memory selection is independent of engine/account selection. No database access."""
import os
from pathlib import Path
import subprocess

CONFLICTS = ('ENGRAM_BIN','ENGRAM_URL','ENGRAM_DATA_DIR','ENGRAM_PORT','ENGRAM_SOCKET',
             'ENGRAM_DATABASE_URL','ENGRAM_SERVER_MODE','ENGRAM_HTTP_TOKEN','ENGRAM_STARTUP_POLICY')
ERROR = 'No se pudo verificar la memoria compartida. Inicia un servidor Engram compatible en 127.0.0.1:7437 y vuelve a intentarlo.'


def selection(env, config):
    mode = config.get('memory_mode', 'private')
    if mode not in ('private', 'shared'):
        raise ValueError('Selecciona memoria privada o compartida.')
    result = dict(env)
    if mode == 'shared':
        if any(str(env.get(key, '')).strip() for key in CONFLICTS):
            raise ValueError('La memoria compartida entra en conflicto con variables ENGRAM heredadas. Retíralas del entorno de ARISE y vuelve a abrirlo.')
        result['ARISE_MEMORY_MODE'] = 'shared'
    else:
        result.pop('ARISE_MEMORY_MODE', None)
    return result


def validate(config, env=None):
    source = selection(os.environ if env is None else env, config)
    if config.get('memory_mode', 'private') != 'shared':
        return
    configured = config.get('pi_command', [])
    if (len(configured) != 2 or Path(configured[0]).stem.lower() != 'node'
            or not (Path(config.get('gentle_path', ''))/'runtime/gentle-shell-bundled.mjs').is_file()):
        raise RuntimeError(ERROR)
    try:
        command = [config['pi_command'][0], str(Path(__file__).parent/'resources/shared-memory.mjs'),
                   '--verify', config['gentle_path']]
        result = subprocess.run(command, env=source, capture_output=True, timeout=8,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode != 0:
            raise RuntimeError(ERROR)
    except (OSError, subprocess.TimeoutExpired, KeyError, IndexError) as error:
        raise RuntimeError(ERROR) from error
