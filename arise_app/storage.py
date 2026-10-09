from __future__ import annotations
import base64
import ctypes
import json
import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path

DEFAULTS = {
    "workspace": "", "pi_command": ["pi"], "pi_extra_args": [],
    "voice_model": "gpt-realtime-2.1", "voice": "marin", "voice_provider": "openai",
    "code_enabled": False, "agent_provider": "", "agent_model": "", "thinking": "medium", "gentle_path": "",
    "wake_enabled": False, "wake_phrases": ["oye arise", "hey arise", "hola arise"],
    "wake_model": "", "input_device": None, "output_device": None, "voice_timeout": 60,
    "local_stt_model": "small", "piper_model": "", "piper_command": ["piper"],
    "orb_size": 96, "orb_position": None, "pinned": True, "reduced_motion": False, "orb_animation": "sprite",
    "onboarding_complete": False,
    "active_chat": "",
    "gmail_client_file": "",
    "mcp": {
        "screenview": {"command": ["screenview-mcp"], "enabled": True},
        "inputcontrol": {"command": ["inputcontrol-mcp"], "enabled": True},
        "forge": {"command": ["forge-mcp"], "enabled": True},
        "transcripcion": {"command": ["transcripcion-mcp"], "enabled": True},
    },
}


class Storage:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.root / "arise.db", check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS conversations(id TEXT PRIMARY KEY,title TEXT,created REAL,pi_file TEXT);
        CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY,conversation TEXT,role TEXT,text TEXT,created REAL);
        CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,payload TEXT,created REAL);
        """)
        self.config_path = self.root / "settings.json"
        self.config = json.loads(json.dumps(DEFAULTS))
        if self.config_path.exists():
            self.config.update(json.loads(self.config_path.read_text(encoding="utf-8-sig")))
        if not self.config["workspace"]:
            self.config["workspace"] = str(self.root / "Workspace")
        Path(self.config["workspace"]).mkdir(parents=True, exist_ok=True)
        self.save_config(self.config)

    def save_config(self, config):
        with self.lock:
            self.config = config
            temp = self.config_path.with_suffix(".tmp")
            temp.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
            os.replace(temp, self.config_path)

    def conversations(self):
        with self.lock:
            return [dict(r) for r in self.db.execute("SELECT * FROM conversations ORDER BY created DESC")]

    def create_conversation(self):
        identity = uuid.uuid4().hex
        with self.lock, self.db:
            self.db.execute("INSERT INTO conversations VALUES(?,?,?,NULL)", (identity, "Nueva conversación", time.time()))
        return identity

    def messages(self, conversation):
        with self.lock:
            return [dict(r) for r in self.db.execute("SELECT * FROM messages WHERE conversation=? ORDER BY created,rowid", (conversation,))]

    def message(self, conversation, role, text):
        identity = uuid.uuid4().hex
        with self.lock, self.db:
            self.db.execute("INSERT INTO messages VALUES(?,?,?,?,?)", (identity, conversation, role, text, time.time()))
            if role == "user":
                self.db.execute("UPDATE conversations SET title=? WHERE id=? AND title='Nueva conversación'", (text[:45], conversation))
        return identity

    def set_pi_file(self, conversation, filename):
        with self.lock, self.db:
            self.db.execute("UPDATE conversations SET pi_file=? WHERE id=?", (filename, conversation))


class DataBlob(ctypes.Structure):
    _fields_ = [("size", ctypes.c_ulong), ("data", ctypes.POINTER(ctypes.c_ubyte))]


def protect(data, decrypt=False):
    """Windows DPAPI, bound to the signed-in user. No plaintext token fallback."""
    if os.name != "nt":
        raise RuntimeError("Guardar credenciales está disponible solo en Windows (DPAPI).")
    buffer = ctypes.create_string_buffer(data)
    source = DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    output = DataBlob()
    crypt = ctypes.windll.crypt32
    crypt.CryptProtectData.argtypes = [ctypes.POINTER(DataBlob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(DataBlob)]
    crypt.CryptUnprotectData.argtypes = crypt.CryptProtectData.argtypes
    crypt.CryptProtectData.restype = crypt.CryptUnprotectData.restype = ctypes.c_int
    ctypes.windll.kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    ctypes.windll.kernel32.LocalFree.restype = ctypes.c_void_p
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    # CRYPTPROTECT_UI_FORBIDDEN
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output.data, output.size)
    finally:
        ctypes.windll.kernel32.LocalFree(output.data)


class Vault:
    def __init__(self, root, name="gmail"):
        self.path = Path(root) / (name + ".dpapi")

    def read(self):
        if not self.path.exists():
            return None
        return json.loads(protect(base64.b64decode(self.path.read_bytes()), decrypt=True))

    def write(self, value):
        payload = base64.b64encode(protect(json.dumps(value).encode()))
        temp = self.path.with_suffix(".tmp")
        temp.write_bytes(payload)
        os.replace(temp, self.path)

    def clear(self):
        self.path.unlink(missing_ok=True)
