"""Resident engine with a single-instance lock and authenticated local UI bridge."""
import argparse
import base64
import json
import os
import secrets
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path
from .assistant import Assistant
from .server import make_server
from .voice import VoiceService
from .hotkeys import Hotkeys
from .storage import protect
from .bundle import configure_bundle, application_root
from .discovery import detect


def descriptor_path(root): return Path(root) / "daemon.json"


def encode_token(token):
    raw = token.encode()
    return base64.b64encode(protect(raw) if os.name == "nt" else raw).decode()


def decode_token(value):
    raw = base64.b64decode(value)
    return (protect(raw, decrypt=True) if os.name == "nt" else raw).decode()


def read_descriptor(root):
    path = descriptor_path(root)
    try:
        data = json.loads(path.read_text())
        if not data["url"].startswith("http://127.0.0.1:"): return None
        data["token"] = decode_token(data["token"])
        return data
    except (OSError, ValueError, KeyError, RuntimeError): return None


def ping(descriptor):
    if not descriptor: return False
    try:
        req = urllib.request.Request(descriptor["url"] + "/api/status", headers={"Authorization": "Bearer " + descriptor["token"]})
        with urllib.request.urlopen(req, timeout=1) as result:
            return json.load(result).get("version") == "0.2.0"
    except Exception: return False


def ensure_daemon(root, timeout=25):
    data = read_descriptor(root)
    if ping(data): return data
    root = Path(root); root.mkdir(parents=True, exist_ok=True)
    frozen = getattr(sys, "frozen", False)
    command = [sys.executable, "--daemon", "--data-dir", str(root)] if frozen else [sys.executable, "-m", "arise_app.daemon", "--data-dir", str(root)]
    supervisor = application_root() / "ARISE-host.exe"
    if os.name == "nt" and supervisor.is_file():
        command = [str(supervisor), "--engine", sys.executable, "--data-dir", str(root)]
        if not frozen: command += ["--python-module", "arise_app.daemon"]
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1]) + os.pathsep + os.environ.get("PYTHONPATH", "")}
    flags = (getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)) if os.name == "nt" else 0
    process = subprocess.Popen(command, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=flags, start_new_session=os.name != "nt")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        data = read_descriptor(root)
        if ping(data): return data
        if process.poll() is not None and process.returncode != 0:
            raise RuntimeError("El proceso residente no pudo iniciar. Ejecuta python -m arise_app.daemon para diagnosticarlo.")
        time.sleep(.1)
    raise RuntimeError("El proceso residente no respondió a tiempo.")


class InstanceLock:
    def __init__(self, root):
        self.file = open(Path(root) / "daemon.lock", "a+b")
        self.file.seek(0); self.file.write(b"0"); self.file.flush(); self.file.seek(0)
    def acquire(self):
        try:
            if os.name == "nt":
                import msvcrt; msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl; fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError: return False
    def close(self): self.file.close()


def main():
    parser = argparse.ArgumentParser(description="ARISE resident engine")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--no-audio", action="store_true")
    args = parser.parse_args()
    root = Path(args.data_dir); root.mkdir(parents=True, exist_ok=True)
    lock = InstanceLock(root)
    if not lock.acquire(): lock.close(); return 0
    if getattr(sys, "frozen", False): os.environ.setdefault("ARISE_CHAT_ROOT", str(application_root() / "chat"))
    runtime = Assistant(root)
    found = detect(runtime.storage.config)
    configure_bundle(runtime)
    changes = {key: found[key] for key in ("pi_command", "gentle_path") if found.get(key)}
    if found.get("gentle_installed_package") and not found.get("gentle_path"):
        changes["gentle_path"] = ""
    if changes: runtime.settings(changes)
    server = make_server(runtime)
    voice = VoiceService(runtime)
    runtime.voice_service = voice
    hotkeys = Hotkeys(voice.wake, lambda: (voice.end_session(), threading.Thread(target=runtime.stop, daemon=True).start()))
    if not args.no_audio:
        voice.start(); hotkeys.start()
    temporary = root / "daemon.tmp"
    temporary.write_text(json.dumps({"url": runtime.url, "token": encode_token(runtime.token), "pid": os.getpid(), "version": "0.2.0"}))
    if os.name != "nt": temporary.chmod(0o600)
    os.replace(temporary, descriptor_path(root))
    runtime.emit("notice", {"text": "Proceso residente activo. Pi y las herramientas se conectan cuando se necesitan."})
    try: server.serve_forever(poll_interval=.1)
    except KeyboardInterrupt: pass
    finally:
        voice.close(); hotkeys.close(); runtime.close(); server.server_close(); runtime.storage.db.close()
        descriptor_path(root).unlink(missing_ok=True); lock.close()
    return 0

if __name__ == "__main__": raise SystemExit(main())
