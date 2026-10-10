"""Classify subprocess failures without returning arbitrary logs or credentials."""
import subprocess
import threading


def failure_hint(text):
    text = text.lower()
    for needles, message in (
        (("epipe", "broken pipe"), "EPIPE: el proceso remoto cerró su canal de comunicación."),
        (("certificate_verify_failed", "certificate verify failed"), "TLS: no se pudo validar el certificado; revisa el certificado del proxy o servidor."),
        (("no module named pip",), "El Python integrado no puede cargar pip."),
        (("backendunavailable", "cannot import 'setuptools", "no module named setuptools"), "El entorno de compilación no puede cargar setuptools; revisa el runtime Python integrado."),
        (("no matching distribution", "requires a different python"), "Hay dependencias incompatibles con esta versión de Python o Windows."),
        (("modulenotfounderror", "err_module_not_found", "cannot find module"), "Falta un módulo requerido por el proceso."),
        (("eaddrinuse", "address already in use"), "El puerto está ocupado por otro proceso."),
        (("econnrefused", "connection refused", "newconnectionerror"), "El servidor de destino no está escuchando."),
        (("401", "unauthorized", "invalid api key"), "El proveedor rechazó la autenticación."),
        (("403", "forbidden"), "El servidor denegó el acceso."),
        (("enotfound", "getaddrinfo", "name resolution"), "No se pudo resolver el servidor DNS."),
    ):
        if any(needle in text for needle in needles):
            return message
    return "No hay una causa reconocida en el diagnóstico del proceso."


class DiagnosticTail:
    def __init__(self):
        self.lock = threading.Lock()
        self.tail = b""
        self.done = threading.Event()

    def drain(self, pipe):
        try:
            while True:
                data = pipe.read1(4096)
                if not data:
                    break
                with self.lock:
                    self.tail = (self.tail + data)[-16384:]
        finally:
            self.done.set()

    def hint(self):
        with self.lock:
            return failure_hint(self.tail.decode("utf-8", errors="replace"))


def checked_run(command, label, **kwargs):
    """Bound captured output, including when pip is unusually noisy."""
    timeout = kwargs.pop("timeout", 480)
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs) as process:
        tail = DiagnosticTail()
        thread = threading.Thread(target=tail.drain, args=(process.stdout,), daemon=True)
        thread.start()
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            raise RuntimeError(f"{label}: tiempo de espera agotado.") from None
        finally:
            tail.done.wait(1)
        if code:
            raise RuntimeError(f"{label} (salida {code}): {tail.hint()}")
