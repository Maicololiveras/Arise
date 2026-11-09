"""Wait for the native renderer to clear overlays before desktop operations."""
import contextlib
import secrets
import threading
import time


class DesktopLayout:
    def __init__(self, runtime):
        self.runtime = runtime
        self.seen = 0.0
        self.pending = {}
        self.lock = threading.Lock()

    def heartbeat(self):
        self.seen = time.monotonic()

    def acknowledge(self, identifier):
        with self.lock:
            event = self.pending.get(identifier)
            if event: event.set()
        return {"acknowledged": event is not None}

    @contextlib.contextmanager
    def clear(self, service, tool):
        excluded = {"control_status", "stop_control", "get_screen_size", "get_mouse_position",
                    "forge_speak", "forge_audio_emit", "forge_get_state", "forge_list_sessions",
                    "forge_list_skills", "forge_get_skill", "forge_get_templates", "forge_get_observation_status"}
        enabled = self.runtime.storage.config.get("desktop_auto_clear", True)
        if not enabled or service not in ("screenview", "inputcontrol", "forge") or tool in excluded or time.monotonic() - self.seen > 3:
            yield
            return
        identifier = secrets.token_urlsafe(24)
        event = threading.Event()
        with self.lock: self.pending[identifier] = event
        self.runtime.emit("desktop_layout", {"action": "prepare", "id": identifier})
        try:
            if not event.wait(3):
                raise RuntimeError("ARISE no pudo apartar su panel. Vuelve a abrir el panel antes de reintentar la herramienta.")
            yield
        finally:
            with self.lock: self.pending.pop(identifier, None)
            self.runtime.emit("desktop_layout", {"action": "done", "id": identifier})
