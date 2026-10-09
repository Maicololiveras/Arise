"""Thin native UI client. Tasks, voice, credentials and device tools live in daemon."""
import json
import urllib.error
import urllib.request
from pathlib import Path

class RemoteStorage:
    def __init__(self, remote, root):
        self.remote, self.root = remote, Path(root)
        self.config = self.remote.request("config")
    def save_config(self, config):
        self.remote.request("preferences", {key: config[key] for key in ("orb_position", "orb_size", "pinned", "reduced_motion") if key in config})
        self.config = self.remote.request("config")
    def conversations(self): return self.remote.request("conversations")["conversations"]
    def messages(self, identity): return self.remote.request("messages")["messages"]

class RemoteCredentials:
    def __init__(self, remote): self.remote = remote
    def save(self, provider, value, persist=True): self.remote.request("credential", {"provider": provider, "value": value, "persist": persist})

class RemoteVault:
    def __init__(self, remote): self.remote = remote
    def clear(self): return self.remote.request("gmail/disconnect", {})

class RemoteGmail:
    def __init__(self, remote): self.remote = remote; self.vault = RemoteVault(remote)
    def connect(self): return self.remote.request("gmail/connect", {})

class RemotePi:
    def __init__(self, remote): self.remote = remote
    def request(self, record): return self.remote.request("pi", record)

class RemoteActive:
    def __init__(self, voice): self.voice = voice
    def is_set(self): return self.voice.remote.request("voice/status")["active"]

class RemoteVoice:
    def __init__(self, remote): self.remote = remote; self.active = RemoteActive(self)
    @property
    def muted(self): return self.remote.request("voice/status")["muted"]
    def wake(self, text=""): return self.remote.request("voice/wake", {"text": text})
    def end_session(self): return self.remote.request("voice/end", {})
    def mute(self, muted=True): return self.remote.request("voice/mute", {"muted": muted})
    def start(self): pass
    def close(self): pass  # closing a renderer never stops the daemon

class RemoteState:
    def __init__(self, remote): self.remote = remote
    def update(self, state=None, **changes): return self.remote.request("orb", {"state": state, **changes})

class RemoteAssistant:
    is_remote = True
    def __init__(self, descriptor, root):
        self.url, self.token = descriptor["url"], descriptor["token"]
        self.storage = RemoteStorage(self, root)
        self.credentials = RemoteCredentials(self); self.gmail = RemoteGmail(self); self.pi = RemotePi(self)
        self.voice_service = RemoteVoice(self); self.orb = RemoteState(self)
        self.local_events = []; self.local_seq = 0
    def request(self, path, body=None, timeout=40):
        headers = {"Authorization": "Bearer " + self.token, "Content-Type": "application/json"}
        data = None if body is None else json.dumps(body, ensure_ascii=False).encode()
        request = urllib.request.Request(self.url + "/api/" + path, data=data, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as result: return json.load(result)
        except urllib.error.HTTPError as error:
            try: message = json.load(error).get("error", "La operación falló")
            except Exception: message = "La operación falló"
            raise RuntimeError(message) from None
        except (OSError, TimeoutError): raise RuntimeError("El proceso residente no responde. Reinícialo desde la bandeja.") from None
    @property
    def conversation(self): return self.status()["conversation"]
    @property
    def busy(self): return self.status()["busy"]
    def status(self): return self.request("status")
    def emit(self, kind, data): return self.request("notice", {"kind": kind, "data": data})
    def events_after(self, after): return self.request("events?after=" + str(after), timeout=1)
    def connect_pi(self): return self.request("connect", {})
    def connect_mcp(self, name):
        data = self.request("mcp/connect", {"name": name})
        return type("Catalog", (), {"tools": data["tools"]})()
    def settings(self, changes):
        result = self.request("config", changes); self.storage.config = self.request("config"); return result
    def steer(self, text): return self.request("prompt", {"text": text})
    def stop(self): return self.request("stop", {})
    def switch_conversation(self, identity=None):
        result = self.request("conversation", {"id": identity}); self.storage.config = self.request("config"); return result
    def project_catalog(self): return self.request("projects")
    def select_project(self, path):
        result = self.request("project", {"path": path}); self.storage.config = self.request("config"); return result
    def session_command(self, command): return self.request("session/command", {"command": command})
    def answer_dialog(self, data): return self.request("dialog", data)
    def approve(self, identity, approved): return self.request("approval", {"id": identity, "approved": approved})
    def set_desktop(self, enabled): return self.request("desktop", {"enabled": enabled})
    def call_tool(self, name, arguments): return self.request("tools/call", {"name": name, "arguments": arguments})
    def close(self): pass
    def shutdown(self): return self.request("shutdown", {})
