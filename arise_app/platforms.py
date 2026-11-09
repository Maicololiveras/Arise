"""Native distribution identity and platform-specific storage, without emulation guesses."""
import os
import platform
import sys
from pathlib import Path


def target(system=None, machine=None):
    system = system or platform.system()
    machine = (machine or platform.machine()).lower()
    systems = {"Windows":"windows", "Linux":"linux", "Darwin":"macos"}
    architectures = {"x86_64":"x64", "amd64":"x64", "arm64":"arm64", "aarch64":"arm64"}
    if system not in systems or machine not in architectures:
        raise RuntimeError("Unsupported operating system or processor architecture.")
    return systems[system] + "-" + architectures[machine]


def data_directory():
    if sys.platform == "win32":return Path(os.environ.get("LOCALAPPDATA",Path.home()/"AppData/Local"))/"ARISE-Orb"
    if sys.platform == "darwin":return Path.home()/"Library/Application Support/ARISE-Orb"
    return Path(os.environ.get("XDG_DATA_HOME",Path.home()/".local/share"))/"ARISE-Orb"


def bundled_executable(root, relative):
    root = Path(root)
    native = root/(relative + (".exe" if os.name == "nt" else ""))
    # Retain compatibility with legacy bundle inspection and recovery.
    legacy = root/(relative + ".exe")
    return native if native.is_file() or not legacy.is_file() else legacy


def has_vosk():
    import importlib.util
    return importlib.util.find_spec("vosk") is not None


def native_preview():
    import json
    marker = Path(__file__).parent / 'resources/update-channel.json'
    return marker.is_file() and json.loads(marker.read_text(encoding='utf-8')).get('format') == 'native-preview'
