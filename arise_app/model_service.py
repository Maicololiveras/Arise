"""Own an optional local inference process; readiness requires a model catalog."""
import threading
import time
import urllib.error
from .processes import JsonProcess


class ModelService:
    def __init__(self):
        self.lock = threading.RLock()
        self.process = None
        self.state = "stopped"
        self.error = ""
        self.retry_after = 0.0
        self.cancel = threading.Event()

    def snapshot(self):
        process = self.process
        state = "failed" if process and process.process.poll() is not None else self.state
        return {"state": state, "error": self.error, "managed": process is not None}

    def ensure(self, probe, command, timeout=60):
        with self.lock:
            self.cancel.clear()
            if time.monotonic() < self.retry_after:
                raise RuntimeError(self.error)
            try:
                return self._ensure(probe, command, timeout)
            except Exception as error:
                self.state = "failed"
                self.error = str(error)
                self.retry_after = time.monotonic() + 30
                if self.process:
                    self.process.close()
                    self.process = None
                raise

    def _ensure(self, probe, command, timeout):
        # Reuse a healthy external server. Never terminate it or start a duplicate.
        reachable = False
        try:
            data = probe()
            reachable = True
            if data.get("data"):
                self.state, self.error = "ready", ""
                return data
        except urllib.error.HTTPError as error:
            if error.code != 503:
                raise RuntimeError(f"Servidor local respondió HTTP {error.code}; revisa autenticación y URL.") from None
            reachable = True  # llama-server publishes 503 while loading weights.
        except (OSError, urllib.error.URLError):
            pass
        if self.process and self.process.process.poll() is not None:
            self.process.close()
            self.process = None
        if not reachable and not self.process:
            if not command:
                raise RuntimeError("El servidor local no está disponible. Inícialo con un modelo cargado o configura su comando de arranque en Voz y audio.")
            self.process = JsonProcess(command)
        self.state = "starting"
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.cancel.is_set():
                raise RuntimeError("Arranque del servidor local cancelado.")
            if self.process and self.process.process.poll() is not None:
                raise RuntimeError("El servidor de modelos se cerró. " + self.process.diagnostics.hint())
            try:
                data = probe()
                if data.get("data"):
                    self.state, self.error = "ready", ""
                    return data
            except urllib.error.HTTPError as error:
                if error.code != 503:
                    raise RuntimeError(f"Servidor local respondió HTTP {error.code}; revisa autenticación y URL.") from None
            except (OSError, urllib.error.URLError):
                pass
            self.cancel.wait(.1)
        raise RuntimeError("El servidor local no publicó modelos a tiempo. Revisa el modelo y los argumentos de arranque.")

    def close(self):
        self.cancel.set()
        with self.lock:
            if self.process:
                self.process.close()
                self.process = None
            self.state, self.error, self.retry_after = "stopped", "", 0.0
