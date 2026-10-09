from . import __version__
"""ARISE application services. Pi alone owns the task execution loop."""
import json
import mimetypes
import os
import threading
import time
import uuid
from pathlib import Path
from .runtime import Runtime, SYSTEM
from .credentials import Credentials
from .state import StateBus

class Assistant(Runtime):
    def __init__(self, data_dir):
        super().__init__(data_dir)
        self.credentials = Credentials(self.storage.root)
        self.orb = StateBus(self.emit)
        self.approvals = {}
        self.action_lock = threading.RLock()
        self.stop_generation = 0
        self.voice_service = None
        with self.storage.lock, self.storage.db:
            for row in self.storage.db.execute("SELECT id,payload FROM tasks ORDER BY created DESC LIMIT 100"):
                task = json.loads(row["payload"])
                if task["status"] == "running":
                    task.update(status="error", error="El proceso residente se interrumpió. Verifica el resultado externo antes de repetir la acción.")
                self.tasks[row["id"]] = task
            for task in self.tasks.values(): self.persist_task(task)

    def persist_task(self, task):
        with self.storage.lock, self.storage.db:
            self.storage.db.execute("INSERT OR REPLACE INTO tasks VALUES(?,?,?)", (task["id"], json.dumps(task, ensure_ascii=False), time.time()))

    def status(self):
        result = super().status()
        result["version"] = __version__
        result["orb"] = vars(self.orb.value).copy()
        result["voice"] = {"provider": self.storage.config["voice_provider"], "model": self.storage.config["voice_model"],
            "configured": self.storage.config["voice_provider"] == "local" or bool(self.credentials.get(self.storage.config["voice_provider"]))}
        result["gentle"] = {"path": self.storage.config.get("gentle_path", ""), "verified": self.pi_state.get("gentleVerified", False)}
        return result

    def connect_pi(self):
        # Base creates the RPC subprocess. A per-process credential environment
        # avoids writing keys to Pi settings or leaking them in command arguments.
        return super().connect_pi()

    def pi_event(self, event):
        super().pi_event(event)
        if event.get("type") == "tool_execution_start":
            self.orb.update("working", activity=str(event.get("toolName", "HERRAMIENTA"))[:24], task=self.current_task)
        elif event.get("type") == "process_closed":
            self.orb.update("error", task=None, control=False, screen=False)

    def prompt(self, text):
        self.orb.update("understanding")
        try:
            result = super().prompt(text)
            self.persist_task(self.tasks[result["task_id"]])
            return result
        except Exception:
            self.orb.update("error")
            raise

    def steer(self, text):
        if not self.busy:
            return self.prompt(text)
        self.storage.message(self.conversation, "user", text)
        self.pi.request({"type": "steer", "message": text})
        self.emit("user", {"text": text})
        return {"task_id": self.current_task, "steering": True}

    def finish_task(self, error=None):
        identity = self.current_task
        super().finish_task(error)
        if identity and hasattr(self, "orb"):
            self.persist_task(self.tasks[identity])
        if hasattr(self, "orb"):
            active_voice = self.voice_service and self.voice_service.active.is_set()
            self.orb.update("error" if error else "listening" if active_voice else "idle", task=None)

    def set_desktop(self, enabled):
        if enabled and os.name != "nt":
            raise RuntimeError("El control real del escritorio requiere Windows.")
        if not enabled:
            return self.stop()
        self.desktop = True
        self.orb.update(control=True)
        return self.status()

    def ask_approval(self, action, preview, timeout=120):
        identity = uuid.uuid4().hex
        pending = {"event": threading.Event(), "approved": False, "generation": self.stop_generation}
        with self.lock:
            self.approvals[identity] = pending
        self.orb.update("waiting_approval")
        self.emit("approval", {"id": identity, "action": action, "preview": preview})
        try:
            pending["event"].wait(timeout)
            if not pending["approved"] or pending["generation"] != self.stop_generation:
                raise RuntimeError("Acción cancelada o no autorizada.")
        finally:
            with self.lock:
                self.approvals.pop(identity, None)
            self.orb.update("working" if self.busy else "idle")

    def approve(self, identity, approved):
        with self.lock:
            pending = self.approvals.get(identity)
            if not pending:
                raise ValueError("La decisión ya no está pendiente.")
            pending["approved"] = approved is True
            pending["event"].set()

    def stop(self):
        self.stop_generation += 1
        self.desktop = False  # revoke before waiting for the agent to abort
        for pending in list(getattr(self, "approvals", {}).values()):
            pending["event"].set()
        result = super().stop()
        if hasattr(self, "orb"):
            self.orb.update(control=False, screen=False)
        return result

    def tool_catalog(self):
        catalog = super().tool_catalog()
        catalog["tools"].extend([
            {"name": "files.write", "description": "Escribe UTF-8 dentro del workspace.", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}, "text": {"type": "string"}}, "required": ["path", "text"]}},
            {"name": "gmail.send_draft", "description": "Solicita confirmación visible para enviar un borrador existente. Nunca repetir un envío ambiguo.", "inputSchema": {"type": "object", "properties": {"draft_id": {"type": "string"}}, "required": ["draft_id"]}},
        ])
        for tool in catalog["tools"]:
            if tool["name"] == "gmail.draft":
                tool["inputSchema"]["properties"]["attachments"] = {"type": "array", "items": {"type": "string"}, "description": "Rutas relativas al workspace"}
        return catalog

    def call_tool(self, name, arguments):
        if not isinstance(arguments, dict):
            raise ValueError("arguments debe ser un objeto.")
        if name == "files.write":
            path = self.scoped_path(arguments["path"])
            text = arguments["text"]
            if not isinstance(text, str) or len(text.encode()) > 2_000_000:
                raise ValueError("El archivo supera 2 MB.")
            with self.action_lock:
                path.parent.mkdir(parents=True, exist_ok=True)
                temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
                temp.write_text(text, encoding="utf-8")
                os.replace(temp, path)
            return self.wrap({"path": str(path), "written": True})
        if name == "gmail.draft":
            attachments = []
            total = 0
            for value in arguments.get("attachments", []):
                path = self.scoped_path(value)
                total += path.stat().st_size
                if total > 15_000_000:
                    raise ValueError("Adjuntos: máximo total 15 MB.")
                attachments.append((path.name, path.read_bytes(), mimetypes.guess_type(path.name)[0] or "application/octet-stream"))
            return self.wrap(self.gmail.draft(arguments["to"], arguments["subject"], arguments["body"], attachments))
        if name == "gmail.send_draft":
            with self.action_lock:
                preview = self.gmail.draft_preview(arguments["draft_id"])
                self.ask_approval(name, preview)
                if not self.gmail.mark_send_attempt(arguments["draft_id"]):
                    raise RuntimeError("Este borrador ya tiene un intento de envío. Comprueba Gmail antes de repetirlo.")
                return self.wrap(self.gmail.send_draft(arguments["draft_id"]))
        desktop_service = name.split(".", 1)[0] in ("inputcontrol", "forge")
        if desktop_service:
            with self.action_lock:
                return super().call_tool(name, arguments)
        if name.startswith("screenview."):
            self.orb.update(screen=True)
            try:
                return super().call_tool(name, arguments)
            finally:
                self.orb.update(screen=False)
        return super().call_tool(name, arguments)

    @staticmethod
    def wrap(result):
        return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}], "isError": False}

    def settings(self, changes):
        if changes.get("local_stt_engine", self.storage.config["local_stt_engine"]) not in ("auto", "vosk", "faster-whisper", "openai-whisper"):
            raise ValueError("Motor de transcripción no compatible.")
        for key in ("voice_provider",):
            if changes.get(key, self.storage.config[key]) not in ("openai", "gemini", "local"):
                raise ValueError("Proveedor de voz no compatible.")
        if changes.get("thinking", self.storage.config["thinking"]) not in ("off", "minimal", "low", "medium", "high", "xhigh"):
            raise ValueError("Esfuerzo inválido.")
        for key in ("wake_enabled", "pinned", "reduced_motion", "onboarding_complete", "local_barge_in"):
            if key in changes and not isinstance(changes[key], bool):
                raise ValueError(f"{key} debe ser booleano")
        if "orb_size" in changes and (type(changes["orb_size"]) is not int or not 48 <= changes["orb_size"] <= 240):
            raise ValueError("Tamaño entre 48 y 240.")
        if 'voice_interrupt_threshold' in changes and (type(changes['voice_interrupt_threshold']) is not int or not 300<=changes['voice_interrupt_threshold']<=10000): raise ValueError('Umbral de interrupción entre 300 y 10000.')
        return super().settings(changes)
