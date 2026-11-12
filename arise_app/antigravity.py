"""Opt-in, pinned Antigravity bridge with ARISE's per-chat authority."""
import json
from pathlib import Path

PACKAGE = '@3d24rd0/pi-antigravity-bridge'
VERSION = '1.3.1'


def validate(config):
    enabled = config.get('antigravity_enabled', False)
    if not isinstance(enabled, bool):
        raise ValueError('La opción Antigravity debe ser booleana.')
    if not enabled:
        return None
    root = Path(config.get('gentle_path', '')).resolve().parent / PACKAGE
    try:
        package = json.loads((root / 'package.json').read_text(encoding='utf-8'))
        valid = package.get('name') == PACKAGE and package.get('version') == VERSION and (root / 'src/entry.ts').is_file()
    except (OSError, ValueError):
        valid = False
    if not valid:
        raise ValueError('Falta Antigravity Bridge compatible. Instala el paquete de ARISE con soporte Antigravity.')
    return root


def environment(source, config):
    env = dict(source)
    # No stale activation may leak into a disabled session.
    env.pop('ARISE_AGY_ROOT', None)
    root = validate(config)
    if root is None:
        return env
    env['ARISE_AGY_ROOT'] = str(root)
    env['AGY_APPROVALS'] = 'shadow'
    env['AGY_APPROVALS_MODE'] = 'ask'
    env['AGY_SKIP_PERMISSIONS'] = 'false'
    env['AGY_READONLY'] = 'false' if config.get('code_enabled') else 'true'
    # Independent CLI delegations and web tools do not use the same provider gate.
    env['AGY_ASK_TOOL'] = 'off'
    env['AGY_WEB_TOOLS'] = 'off'
    return env
