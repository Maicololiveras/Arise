"""Long-lived LF-framed JSON RPC subprocesses; no shell prompt injection."""
from __future__ import annotations
from . import __version__
import json
import os
import queue
import shutil
import subprocess
import threading
import uuid


def executable_argv(command):
    if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
        raise ValueError("El comando debe ser una lista de argumentos.")
    resolved = shutil.which(command[0]) or (command[0] if os.path.isfile(command[0]) else None)
    if not resolved:
        raise RuntimeError(f"No se encontró {command[0]}. Instálalo o configura su ruta.")
    # Avoid cmd.exe / shell=True and preserve JSONL pipes on Windows npm launchers.
    if os.name == "nt" and resolved.lower().endswith((".cmd", ".bat")):
        from pathlib import Path
        if Path(resolved).stem.lower() == "pi":
            root = Path(resolved).parent / "node_modules" / "@earendil-works" / "pi-coding-agent" / "dist" / "cli.js"
            if root.is_file() and shutil.which("node"):
                return [shutil.which("node"), str(root), *command[1:]]
        raise RuntimeError("Configura un ejecutable directo, por ejemplo [node, ruta/cli.js]; no un .cmd.")
    return [resolved, *command[1:]]


class JsonProcess:
    def __init__(self, command, cwd=None, env=None, on_event=None):
        self.pending = {}
        self.lock = threading.RLock()
        self.write_lock = threading.Lock()
        self.on_event = on_event or (lambda e: None)
        self.closed = False
        self.process = subprocess.Popen(
            executable_argv(command), cwd=cwd, env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), start_new_session=os.name != "nt",
        )
        threading.Thread(target=self._read, daemon=True).start()
        threading.Thread(target=self._drain_error, daemon=True).start()

    def _drain_error(self):
        # Drain diagnostics but never expose raw logs that might contain credentials.
        while self.process.stderr.read(4096):
            pass

    def _read(self):
        try:
            while True:
                raw = self.process.stdout.readline()  # binary: LF only, including U+2028 in JSON strings
                if not raw:
                    break
                try:
                    event = json.loads(raw.decode("utf-8"))
                except (ValueError, UnicodeError):
                    continue
                if not isinstance(event, dict):
                    continue
                with self.lock:
                    target = self.pending.get(event.get("id"))
                if target and (event.get("type") == "response" or "result" in event or "error" in event):
                    target.put(event)
                else:
                    self.on_event(event)
        finally:
            with self.lock:
                for target in self.pending.values():
                    target.put({"error": {"message": "El proceso se cerró."}})
            if not self.closed:
                self.on_event({"type": "process_closed"})

    def send(self, record):
        with self.write_lock:
            if self.closed or self.process.poll() is not None:
                raise RuntimeError("El proceso no está conectado.")
            self.process.stdin.write((json.dumps(record, ensure_ascii=False) + "\n").encode("utf-8"))
            self.process.stdin.flush()

    def request(self, record, timeout=30):
        identity = uuid.uuid4().hex
        target = queue.Queue()
        with self.lock:
            self.pending[identity] = target
        try:
            self.send({**record, "id": identity})
            result = target.get(timeout=timeout)
            if "error" in result or result.get("success") is False:
                err = result.get("error", "La operación falló.")
                raise RuntimeError(err.get("message", "La operación falló.") if isinstance(err, dict) else str(err))
            return result
        except queue.Empty:
            raise TimeoutError("La operación no respondió a tiempo; no se reintentó automáticamente.") from None
        finally:
            with self.lock:
                self.pending.pop(identity, None)

    def close(self):
        with self.lock:
            if self.closed: return
            self.closed = True
        if os.name == "nt":
            import psutil
            descendants=[]
            if self.process.poll() is None:
                try: descendants=psutil.Process(self.process.pid).children(recursive=True)
                except psutil.NoSuchProcess: pass
                self.process.terminate()
                try: self.process.wait(timeout=3)
                except subprocess.TimeoutExpired: self.process.kill(); self.process.wait(timeout=3)
            for child in descendants:
                try: child.terminate()
                except psutil.NoSuchProcess: pass
            _,alive=psutil.wait_procs(descendants,timeout=3)
            for child in alive:
                try: child.kill()
                except psutil.NoSuchProcess: pass
            psutil.wait_procs(alive,timeout=3)
        else:
            import signal
            try: os.killpg(self.process.pid,signal.SIGTERM)
            except ProcessLookupError: pass
            try: self.process.wait(timeout=3)
            except subprocess.TimeoutExpired: pass
            # The process group belongs only to this managed JSONL session.
            try: os.killpg(self.process.pid,signal.SIGKILL)
            except ProcessLookupError: pass
            self.process.wait(timeout=3)
        for pipe in (self.process.stdin, self.process.stdout, self.process.stderr):
            try:
                pipe.close()
            except OSError:
                pass


class McpClient:
    def __init__(self, command, cwd=None):
        self.rpc = JsonProcess(command, cwd=cwd)
        self.operation_lock = threading.Lock()
        try:
            self.rpc.request({"jsonrpc": "2.0", "method": "initialize", "params": {
                "protocolVersion": "2024-11-05", "capabilities": {},
                "clientInfo": {"name": "arise", "version": __version__},
            }}, timeout=20)
            self.rpc.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
            self.tools = []
            cursor = None
            for _ in range(20):
                result = self.rpc.request({"jsonrpc": "2.0", "method": "tools/list", "params": {"cursor": cursor} if cursor else {}})["result"]
                self.tools.extend(result.get("tools", []))
                cursor = result.get("nextCursor")
                if not cursor:
                    break
        except Exception:
            self.rpc.close()
            raise

    def call(self, name, arguments, timeout=90):
        if not any(t["name"] == name for t in self.tools):
            raise ValueError("La herramienta no figura en el catálogo real.")
        with self.operation_lock:
            return self.rpc.request({"jsonrpc": "2.0", "method": "tools/call", "params": {
                "name": name, "arguments": arguments,
            }}, timeout=timeout)["result"]

    def close(self):
        self.rpc.close()
