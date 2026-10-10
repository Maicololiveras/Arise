"""Detect installed Pi and Gentle Shell without installing or running unknown code."""
import json
import os
import shutil
import subprocess
from pathlib import Path


def command_available(command):
    """Resolve launchers and reject missing script arguments, not only missing hosts."""
    from .processes import executable_argv
    try:
        resolved = executable_argv(command)
    except (ValueError, RuntimeError, OSError):
        return False
    return all(Path(arg).is_file() for arg in resolved[1:]
               if arg.lower().endswith(('.js', '.mjs', '.cjs', '.py')))


def resolve_pi(command=None):
    if command_available(command):
        from .processes import executable_argv
        try: return executable_argv(command)
        except RuntimeError: pass
    node = shutil.which("node")
    pi = shutil.which("pi")
    if pi:
        from .processes import executable_argv
        try: return executable_argv([pi])
        except RuntimeError: pass
    roots = [Path(os.getenv("APPDATA", Path.home())) / "npm", Path.home() / ".npm-global", Path.home() / ".local"]
    for root in roots:
        for prefix in (root / "node_modules", root / "lib/node_modules"):
            cli = prefix / "@earendil-works/pi-coding-agent/dist/cli.js"
            if node and cli.is_file(): return [node, str(cli)]
    return None


def gentle_valid(path):
    path = Path(path)
    try:
        package = json.loads((path / "package.json").read_text())
        return package.get("name") in ("gentle-pi", "gentle-shell") and (path / "extensions").is_dir()
    except (OSError, ValueError): return False


def installed_pi_version(command):
    for part in command or []:
        path = Path(part)
        if not path.is_file(): continue
        for parent in list(path.resolve().parents)[:4]:
            package = parent / 'package.json'
            if not package.is_file(): continue
            try:
                data = json.loads(package.read_text(encoding='utf-8'))
                if data.get('name') == '@earendil-works/pi-coding-agent': return data.get('version')
            except (ValueError, OSError): pass
    return None


def detect_gentle_installation():
    """Recover a provisioned pnpm Gentle install after an interrupted wizard."""
    node = shutil.which("node")
    pnpm = shutil.which("pnpm")
    if not pnpm and os.name == "nt":
        candidate = Path(os.getenv("LOCALAPPDATA", "")) / "pnpm/pnpm.cmd"
        if candidate.is_file(): pnpm = str(candidate)
    if not node or not pnpm: return None
    options = dict(capture_output=True, text=True, encoding="utf-8", timeout=20,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        listing_env = dict(os.environ)
        if os.name == "nt":
            pnpm_bin = str(Path(os.getenv("LOCALAPPDATA", "")) / "pnpm/bin")
            listing_env["PATH"] = pnpm_bin + os.pathsep + listing_env.get("PATH", "")
        listing = subprocess.run([pnpm, "list", "-g", "--depth", "0", "--json"], env=listing_env, **options)
        if listing.returncode: return None
        roots = [item.get("dependencies", {}).get("gentle-pi", {}).get("path")
                 for item in json.loads(listing.stdout)]
        roots = [root for root in roots if root]
        if len(roots) != 1 or not gentle_valid(roots[0]): return None
        probe = Path(__file__).parent / "resources/probe-gentle.mjs"
        result = subprocess.run([node, str(probe), roots[0]], **options)
        if result.returncode: return None
        from .gentle_setup import validate_result
        return validate_result(json.loads(result.stdout), node)
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired):
        return None


def detect(config, agent_dir=None):
    if agent_dir is None and not config.get("gentle_agent_home"):
        recovered = detect_gentle_installation()
        if recovered:
            return {**recovered, "agent_dir": recovered["gentle_agent_home"],
                    "package_sources": [], "model_providers": [], "gentle_installed_package": True}
    agent_dir = Path(agent_dir or config.get("gentle_agent_home") or os.getenv("PI_CODING_AGENT_DIR", Path.home() / ".pi/agent"))
    pi = resolve_pi(config.get("pi_command"))
    candidates = []
    current = config.get("gentle_path")
    if current: candidates.append(Path(current))
    settings = agent_dir / "settings.json"
    providers, package_sources = [], []
    if settings.is_file():
        try:
            data = json.loads(settings.read_text(encoding="utf-8-sig"))
            for spec in data.get("packages", []):
                source = spec if isinstance(spec, str) else spec.get("source", "")
                package_sources.append(source)
                if source and not source.startswith(("npm:", "git:", "https:", "ssh:")):
                    candidates.append(Path(source).expanduser() if Path(source).is_absolute() else agent_dir / source)
        except (ValueError, OSError): pass
    candidates.extend([agent_dir / "npm/node_modules/gentle-pi", agent_dir / "npm/node_modules/gentle-shell"])
    git_dir = agent_dir / "git/github.com"
    if git_dir.is_dir():
        for owner in git_dir.iterdir():
            if owner.is_dir():
                candidates.extend(owner / name for name in ("gentle-shell", "gentle-shell-enterprise", "gentle-pi"))
    models = agent_dir / "models.json"
    if models.is_file():
        try: providers = list(json.loads(models.read_text()).get("providers", {}))
        except (ValueError, OSError): pass
    gentle = next((str(p.resolve()) for p in candidates if gentle_valid(p)), None)
    return {"pi_command": pi, "gentle_path": gentle, "agent_dir": str(agent_dir), "package_sources": package_sources,
        "model_providers": providers, "gentle_installed_package": bool(gentle)}


def import_mcp(path):
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    source = data.get("mcpServers", data.get("mcp", {}))
    if not isinstance(source, dict): raise ValueError("No contiene mcpServers o mcp")
    result = {}
    for name, spec in source.items():
        if not isinstance(spec, dict): raise ValueError("Servidor MCP inválido")
        command = spec.get("command")
        if isinstance(command, str): command = [command, *spec.get("args", [])]
        if not isinstance(command, list) or not command: raise ValueError("Esta versión importa MCP stdio con command y args")
        if spec.get("env"):
            # Secrets from arbitrary imported configs are not silently persisted.
            raise ValueError(f"{name}: tiene env; configura sus credenciales fuera del archivo de ajustes de ARISE")
        result[name] = {"command": command, "enabled": not spec.get("disabled", False)}
    return result
