import json
import os
import sys
from pathlib import Path
from .discovery import command_available, gentle_valid, installed_pi_version


def application_root():
    return Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]


def configure_bundle(runtime):
    """Provision missing dependencies from the complete, offline application bundle."""
    bundle = application_root() / "bundle"
    manifest = bundle / "manifest.json"
    if not manifest.is_file():
        return {"bundled": False}
    data = json.loads(manifest.read_text(encoding="utf-8-sig"))
    config = runtime.storage.config
    changes = {}
    # An adopted official installation owns Pi and its home; never replace it
    # with the fallback bundle, including when a user moves/deletes its files.
    official = bool(config.get("gentle_agent_home"))
    if official and (not command_available(config.get("pi_command")) or not gentle_valid(config.get("gentle_path") or "")):
        runtime.emit("notice", {"text": "La instalación de Gentle cambió o está incompleta. Abre Configurar Gentle para repararla con su propio Pi."})
    def expand(value):
        return str(bundle / value[8:]) if value.startswith("@bundle/") else value
    candidates = {}
    for key in ("pi_command", "piper_command", "gentle_path", "wake_model"):
        value = data.get(key)
        if value:
            candidates[key] = [expand(v) for v in value] if isinstance(value, list) else expand(value)
    for key in ("pi_command", "piper_command"):
        value = candidates.get(key)
        if value and not (official and key == "pi_command") and not command_available(config.get(key)):
            if not command_available(value):
                raise RuntimeError("El paquete de " + key + " está incompleto. Extrae de nuevo el ZIP completo de ARISE.")
            changes[key] = value
    gentle = candidates.get("gentle_path")
    if gentle and not official and not gentle_valid(config.get("gentle_path") or ""):
        if not gentle_valid(gentle):
            raise RuntimeError("Gentle Shell no está completo en el ZIP. Extrae de nuevo el paquete de ARISE.")
        changes["gentle_path"] = gentle
    # Gentle 4 requires a compatible Pi even if an older global launcher exists.
    selected = changes.get("gentle_path", config.get("gentle_path", ""))
    try:
        gentle_version = json.loads((Path(selected) / "package.json").read_text(encoding="utf-8")).get("version")
        pi_version = installed_pi_version(changes.get("pi_command", config.get("pi_command")))
        old_pi = pi_version and tuple(int(n) for n in pi_version.split(".")[:3]) < (0, 99, 1)
    except (OSError, ValueError, TypeError):
        gentle_version, old_pi = None, False
    if not official and gentle_version == "4.0.0" and old_pi:
        command = candidates.get("pi_command")
        if not command_available(command):
            raise RuntimeError("Falta el Pi compatible incluido en el ZIP de ARISE.")
        changes["pi_command"] = command
    wake = candidates.get("wake_model")
    if wake and not Path(config.get("wake_model") or "__missing__").is_dir() and Path(wake).is_dir():
        changes["wake_model"] = wake
    tools = dict(config.get("mcp", {}))
    for name, spec in data.get("mcp", {}).items():
        existing = tools.get(name, {})
        if existing.get("enabled") is False or command_available(existing.get("command")):
            continue
        command = [expand(v) for v in spec["command"]]
        if not command_available(command):
            raise RuntimeError(f"El paquete integrado {name} está incompleto. Extrae de nuevo el ZIP completo.")
        tools[name] = {**spec, "command": command, "enabled": True}
    if tools != config.get("mcp", {}):
        changes["mcp"] = tools
    if changes:
        runtime.settings(changes)
        runtime.emit("notice", {"text": "Dependencias integradas configuradas automáticamente: " + ", ".join(changes) + "."})
    return {"bundled": True, "components": data.get("versions", {}), "configured": list(changes)}
