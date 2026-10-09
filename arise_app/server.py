"""Authenticated loopback bridge for the Pi extension; no browser UI or CORS."""
import hmac
import json
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def make_server(runtime, port=0):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"
        def log_message(self, *_): pass

        def reply(self, value, code=200):
            payload = json.dumps(value, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(payload)

        def authorize(self):
            if self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}":
                self.reply({"error": "Host inválido"}, 403); return False
            if self.headers.get("Origin"):
                self.reply({"error": "Los navegadores no tienen acceso a este puente"}, 403); return False
            if not hmac.compare_digest(self.headers.get("Authorization", ""), "Bearer " + runtime.token):
                self.reply({"error": "Sesión no autorizada"}, 401); return False
            return True

        def do_GET(self):
            if not self.authorize(): return
            parsed = urllib.parse.urlparse(self.path)
            try:
                if parsed.path == "/api/status": value = runtime.status()
                elif parsed.path == "/api/tools": value = runtime.tool_catalog()
                elif parsed.path == "/api/config": value = runtime.storage.config
                elif parsed.path == "/api/conversations": value = {"conversations": runtime.storage.conversations()}
                elif parsed.path == "/api/messages": value = {"messages": runtime.storage.messages(runtime.conversation)}
                elif parsed.path == "/api/voice/status": value = {"active": bool(runtime.voice_service and runtime.voice_service.active.is_set()), "muted": bool(runtime.voice_service and runtime.voice_service.muted)}
                elif parsed.path == "/api/events": value = runtime.events_after(int(urllib.parse.parse_qs(parsed.query).get("after", [0])[0]))
                elif parsed.path.startswith("/api/tasks/"):
                    value = runtime.tasks.get(parsed.path.rsplit("/", 1)[1])
                    if value is None: self.reply({"error": "Tarea desconocida"}, 404); return
                else: self.reply({"error": "Ruta desconocida"}, 404); return
                self.reply(value)
            except Exception as error: self.reply({"error": str(error)[:500]}, 400)

        def do_POST(self):
            if not self.authorize(): return
            self.connection.settimeout(10)
            if not self.headers.get("Content-Type", "").startswith("application/json"):
                self.reply({"error": "Se requiere JSON"}, 415); return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 2_000_000: raise ValueError("Tamaño inválido")
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict): raise ValueError("Se requiere un objeto")
                route = urllib.parse.urlparse(self.path).path
                if route == "/api/tools/call": value = runtime.call_tool(data.get("name", ""), data.get("arguments", {}))
                elif route == "/api/prompt": value = runtime.steer(data.get("text", ""))
                elif route == "/api/stop": value = runtime.stop()
                elif route == "/api/config":
                    if runtime.voice_service:
                        runtime.voice_service.end_session()
                    value = runtime.settings(data)
                    if runtime.voice_service: runtime.voice_service.reconfigure()
                elif route == "/api/preferences":
                    allowed = {key: value for key, value in data.items() if key in ("orb_position", "orb_size", "pinned", "reduced_motion")}
                    position = allowed.get("orb_position")
                    if position is not None and (not isinstance(position, list) or len(position) != 2 or not all(type(v) is int for v in position)):
                        raise ValueError("Posición inválida")
                    config = {**runtime.storage.config, **allowed}; runtime.storage.save_config(config); value = {"saved": True}
                elif route == "/api/models/wake/download":
                    from .downloads import download_wake
                    value = {"path": download_wake(runtime.storage.root)}
                elif route == "/api/connect": value = runtime.connect_pi()
                elif route == "/api/mcp/connect": value = {"tools": runtime.connect_mcp(data["name"]).tools}
                elif route == "/api/credential":
                    runtime.credentials.save(data["provider"], data["value"], data.get("persist", True)); value = {"saved": True}
                elif route == "/api/gmail/connect": runtime.gmail.connect(); value = {"connecting": True}
                elif route == "/api/gmail/disconnect": runtime.gmail.vault.clear(); value = {"connected": False}
                elif route == "/api/conversation": value = runtime.switch_conversation(data.get("id"))
                elif route == "/api/dialog": value = runtime.answer_dialog(data)
                elif route == "/api/approval": runtime.approve(data["id"], data.get("approved")); value = {"ok": True}
                elif route == "/api/desktop": value = runtime.set_desktop(data.get("enabled") is True)
                elif route == "/api/orb": value = runtime.orb.update(**data)
                elif route == "/api/notice":
                    if data.get("kind") not in ("notice", "error"): raise ValueError("Evento no permitido")
                    runtime.emit(data["kind"], data["data"]); value = {"ok": True}
                elif route == "/api/pi":
                    if data.get("type") not in ("get_available_models", "get_state", "set_model", "set_thinking_level", "get_commands"):
                        raise ValueError("Comando de configuración no permitido")
                    runtime.connect_pi(); value = runtime.pi.request(data)
                elif route.startswith("/api/voice/"):
                    voice = runtime.voice_service
                    if not voice: raise RuntimeError("Servicio de voz no iniciado")
                    if route.endswith("/wake"): value = {"accepted": voice.wake(data.get("text", ""))}
                    elif route.endswith("/end"): voice.end_session(); value = {"ok": True}
                    elif route.endswith("/mute"): voice.mute(data.get("muted") is True); value = {"ok": True}
                    else: raise ValueError("Operación de voz desconocida")
                elif route == "/api/shutdown":
                    runtime.stop(); value = {"ok": True}
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
                else: self.reply({"error": "Ruta desconocida"}, 404); return
                self.reply(value)
            except (BrokenPipeError, ConnectionResetError): pass
            except Exception as error: self.reply({"error": str(error)[:500]}, 400)

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    runtime.url = f"http://127.0.0.1:{server.server_port}"
    return server
