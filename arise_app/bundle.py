import json
import os
import sys
from pathlib import Path


def application_root():
    return Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]


def configure_bundle(runtime):
    """Only use verified files actually present, never invent installed tools."""
    bundle = application_root() / "bundle"
    manifest = bundle / "manifest.json"
    if not manifest.is_file():
        return {"bundled": False}
    data = json.loads(manifest.read_text(encoding="utf-8-sig"))
    changes = {}
    for key in ("pi_command", "piper_command", "gentle_path", "wake_model"):
        value = data.get(key)
        if value:
            if isinstance(value, list):
                changes[key] = [str(bundle / v[8:]) if v.startswith("@bundle/") else v for v in value]
            else:
                changes[key] = str(bundle / value[8:]) if value.startswith("@bundle/") else value
    tools = {}
    for name, spec in data.get("mcp", {}).items():
        command = [str(bundle / v[8:]) if v.startswith("@bundle/") else v for v in spec["command"]]
        if not Path(command[0]).is_file():
            raise RuntimeError(f"El paquete integrado {name} está incompleto.")
        tools[name] = {"command": command, "enabled": True}
    # Respect saved custom configuration. Configure bundled paths on the first run.
    if not runtime.storage.config["onboarding_complete"]:
        if tools:
            changes["mcp"] = {**runtime.storage.config["mcp"], **tools}
        runtime.settings(changes)
    return {"bundled": True, "components": data.get("versions", {})}
