"""Least-privilege mobile surface, separate from the privileged desktop bridge.

The embedded tailnet node sends normalized HTTP requests over private pipes.
Pairing is initiated on the desktop, bound to one chat, one-use and time limited.
"""
import base64
import hashlib
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import threading
import time
from urllib.parse import urlparse
from .mobile_channel import MobileChannel


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class Devices:
    def __init__(self, storage, channel=None):
        self.storage = storage
        self.channel = MobileChannel.installed() if channel is None else MobileChannel(channel)
        # Identifiers come only from the closed build-channel enum.
        self.pairings = f'mobile_{self.channel.value}_v1_pairings'
        self.devices = f'mobile_{self.channel.value}_v1_devices'
        with storage.lock, storage.db:
            storage.db.execute(f'CREATE TABLE IF NOT EXISTS {self.pairings}(hash TEXT PRIMARY KEY,chat TEXT,expires REAL)')
            storage.db.execute(f'CREATE TABLE IF NOT EXISTS {self.devices}(id TEXT PRIMARY KEY,chat TEXT,name TEXT,hash TEXT,expires REAL,deadline REAL,revoked INTEGER,peer TEXT NOT NULL)')

    def invite(self, chat):
        code = secrets.token_urlsafe(24)
        with self.storage.lock, self.storage.db:
            self.storage.db.execute(f"DELETE FROM {self.pairings} WHERE expires<? OR chat=?", (time.time(), chat))
            self.storage.db.execute(f"INSERT INTO {self.pairings} VALUES(?,?,?)", (digest(code), chat, time.time()+300))
        return {"code": code, "expires_in": 300, "chat": chat}

    def pair(self, code, name, verified=False, peer=""):
        if not isinstance(code, str) or len(code)>200 or not isinstance(name, str) or not 1<=len(name)<=80: raise ValueError("Vinculación inválida.")
        with self.storage.lock, self.storage.db:
            row = self.storage.db.execute(f"SELECT * FROM {self.pairings} WHERE hash=? AND expires>?", (digest(code), time.time())).fetchone()
            if not row: raise ValueError("Código usado o vencido. Genera otro en el PC.")
            self.storage.db.execute(f"DELETE FROM {self.pairings} WHERE hash=?", (digest(code),))
            identity, token = secrets.token_hex(16), secrets.token_urlsafe(32)
            self.storage.db.execute(f"INSERT INTO {self.devices} VALUES(?,?,?,?,?,?,0,?)", (identity, row['chat'], name, digest(token), time.time()+(30*86400 if verified else 900), time.time()+30*86400, peer))
            return token

    def authorize(self, token, peer=""):
        if not isinstance(token, str) or len(token)>200: raise PermissionError("Dispositivo no autorizado.")
        with self.storage.lock:
            row = self.storage.db.execute(f"SELECT id,chat,name FROM {self.devices} WHERE hash=? AND revoked=0 AND peer=? AND expires>? AND deadline>?", (digest(token), peer, time.time(), time.time())).fetchone()
            if not row: raise PermissionError("Sesión vencida o revocada. Vincula nuevamente desde el PC.")
            return dict(row)

    def rotate(self, token, peer=""):
        with self.storage.lock, self.storage.db:
            self.authorize(token, peer)
            fresh = secrets.token_urlsafe(32)
            self.storage.db.execute(f"UPDATE {self.devices} SET hash=?,expires=MIN(MAX(expires,?),deadline) WHERE hash=?", (digest(fresh), time.time()+900, digest(token)))
            return fresh

    def list(self, chat):
        with self.storage.lock:
            return [dict(r) for r in self.storage.db.execute(f"SELECT id,name,expires,deadline,revoked FROM {self.devices} WHERE chat=?", (chat,))]

    def revoke(self, chat, identity):
        with self.storage.lock, self.storage.db:
            self.storage.db.execute(f"UPDATE {self.devices} SET revoked=1 WHERE chat=? AND id=?", (chat, identity))


def mobile_handler(runtime, origin, require_peer=True):
    parsed = urlparse(origin)
    if parsed.scheme != 'https' or not (parsed.hostname or '').endswith('.ts.net') or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.port:
        raise ValueError("Configura el origen HTTPS exacto de Tailscale, sin ruta ni puerto.")
    channel = runtime.devices.channel
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_): pass

        def reply(self, body, code=200, cookie=None, mime='application/json'):
            raw = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
            self.send_response(code)
            for k,v in {'Content-Type': mime, 'Content-Length': str(len(raw)), 'Cache-Control': 'no-store',
                        'Permissions-Policy':'microphone=(self), camera=(), geolocation=()',
                        'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer',
                        'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; media-src 'self' blob:; frame-ancestors 'none'; base-uri 'none'"}.items(): self.send_header(k,v)
            if cookie is not None: self.send_header('Set-Cookie', f'{channel.cookie}={cookie}; Secure; HttpOnly; SameSite=Strict; Path=/; Max-Age={2592000 if cookie else 0}')
            self.end_headers(); self.wfile.write(raw)

        def peer(self):
            peer = self.headers.get('X-Arise-Tailnode', '')
            if require_peer and (not peer or len(peer) > 128):
                raise PermissionError('Identidad de red no disponible.')
            return peer

        def select_protocol(self):
            if not self.path.startswith(channel.api + '/'):
                self.reply({'error':'Protocolo móvil desconocido.'},404)
                return False
            self.path = self.path[len(channel.api):]
            return True

        def context(self):
            cookies = SimpleCookie(self.headers.get('Cookie', ''))
            token = cookies[channel.cookie].value if channel.cookie in cookies else ''
            return token, runtime.devices.authorize(token, self.peer())

        def do_GET(self):
            try:
                public = {'/': ('companion.html', 'text/html; charset=utf-8'),
                          '/companion.js': ('companion.js', 'text/javascript'),
                          '/companion-language.js': ('companion-language.js', 'text/javascript'),
                          '/companion-install.js': ('companion-install.js', 'text/javascript'),
                          '/companion.css': ('companion.css', 'text/css'),
                          '/companion.webmanifest': ('companion.webmanifest', 'application/manifest+json')}
                public.update({f'/companion-icon-{size}.png': (f'companion-icon-{size}.png', 'image/png') for size in (180, 192, 512)})
                if self.path in public:
                    name, mime = public[self.path]
                    body = (Path(__file__).parent/'resources'/name).read_bytes()
                    if name in ('companion.html', 'companion.webmanifest', 'companion.js'):
                        body = body.replace(b'__MOBILE_API__', channel.api.encode()).replace(b'__MOBILE_TITLE__',channel.title.encode())
                    return self.reply(body, mime=mime)
                if not self.select_protocol(): return
                token, device = self.context()
                if self.path == '/agents':
                    with runtime.transition_lock:
                        runtime.devices.authorize(token, self.peer())
                        active = runtime.conversation == device['chat']
                        rows = []
                        available = False
                        if active and runtime.pi and runtime.pi.process.poll() is None:
                            reply = runtime.shell_control(device['chat'], 'list_subagents', {})
                            available = reply.get('supported', False)
                            rows = [{key: str(row.get(key, ''))[:120] for key in ('id', 'agent', 'status', 'lastStep')}
                                    for row in reply.get('data', {}).get('agents', [])[:50]]
                        runtime.devices.authorize(token, self.peer())
                    return self.reply({'agents':rows, 'active':active, 'available':available})
                if self.path != '/messages': return self.reply({'error':'Ruta no disponible.'},404)
                messages = runtime.storage.messages(device['chat'])[-100:]
                with runtime.lock:
                    approvals=[{'id':key,'action':item['action'],'preview':item['preview']} for key,item in runtime.approvals.items()
                               if item.get('chat')==device['chat'] and item.get('generation')==runtime.stop_generation and not item['event'].is_set()]
                return self.reply({'ui_language':runtime.storage.config.get('ui_language','es'),'chat':device['chat'], 'approvals':approvals, 'active':runtime.conversation==device['chat'],
                                   'messages':[{k:m[k] for k in ('id','role','text','created')} for m in messages if m['role'] in ('user','assistant')]})
            except PermissionError as e: self.reply({'error':str(e)},401)

            except (RuntimeError, OSError): self.reply({'error':'Agentes temporalmente no disponibles.'},503)

        def do_POST(self):
            try:
                if not self.select_protocol(): return
                # Browser requests are same-origin only; the desktop bridge stays inaccessible.
                if self.headers.get('Origin') != origin: return self.reply({'error':'Origen no autorizado.'},403)
                if self.headers.get('Content-Type') != 'application/json': return self.reply({'error':'Se requiere JSON.'},415)
                if self.connection is not None:
                    self.connection.settimeout(5)
                length = int(self.headers.get('Content-Length','0'))
                if not 0<length<=(12000000 if self.path=='/prompt' else 1400000 if self.path=='/transcribe' else 40000): raise ValueError('Mensaje demasiado grande.')
                data = json.loads(self.rfile.read(length))
                if not isinstance(data,dict): raise ValueError('JSON inválido.')
                if self.path == '/pair':
                    runtime.mobile_security.verify(data.get('otp'))
                    return self.reply({'paired':True},cookie=runtime.devices.pair(data.get('code'),data.get('name'),verified=True, peer=self.peer()))
                token, device = self.context()
                if self.path == '/logout':
                    runtime.devices.revoke(device['chat'],device['id'])
                    return self.reply({'disconnected':True},cookie='')
                if self.path == '/transcribe':
                    audio=data.get('audio')
                    if not isinstance(audio,str): raise ValueError('Audio inválido.')
                    from .mobile_voice import transcribe
                    text=transcribe(runtime.storage.config,base64.b64decode(audio,validate=True))
                    runtime.devices.authorize(token, self.peer())
                    return self.reply({'text':text})
                if self.path == '/speech':
                    message=next((m for m in runtime.storage.messages(device['chat']) if m['id']==data.get('id') and m['role']=='assistant'),None)
                    if not message: raise ValueError('Respuesta no disponible.')
                    from .mobile_voice import speak
                    audio=speak(message['text'])
                    runtime.devices.authorize(token, self.peer())
                    return self.reply(audio,mime='audio/wav')
                if self.path == '/renew': return self.reply({'renewed':True},cookie=runtime.devices.rotate(token, self.peer()))
                with runtime.transition_lock:
                    runtime.devices.authorize(token, self.peer())
                    if self.path == '/activate':
                        if runtime.conversation!=device['chat']:
                            if runtime.busy or runtime.pi_has_children or any(j['process'].poll() is None for j in runtime.terminals.jobs.values()):
                                return self.reply({'error':'El PC está trabajando en otro chat. Espera a que termine.'},409)
                            runtime.switch_conversation(device['chat'])
                        return self.reply({'active':True})
                    if runtime.conversation != device['chat']: return self.reply({'error':'Abre este chat en el PC para enviar o detener. El historial sigue disponible.'},409)
                    if self.path == '/approval':
                        identity=data.get('id')
                        if not isinstance(identity,str) or not isinstance(data.get('approved'),bool): raise ValueError('Decisión inválida.')
                        with runtime.lock:
                            pending=runtime.approvals.get(identity)
                            if not pending or pending.get('chat')!=device['chat'] or pending.get('generation')!=runtime.stop_generation or pending['event'].is_set():
                                raise ValueError('La decisión ya no está pendiente en este chat.')
                            if data['approved']: runtime.mobile_security.verify(data.get('otp'))
                            runtime.approve(identity,data['approved'])
                        return self.reply({'decided':True})
                    if self.path == '/prompt':
                        text = data.get('text')
                        if not isinstance(text,str) or not 0<len(text.strip())<=12000: raise ValueError('Texto inválido.')
                        # Existing permissions and approval UI still govern every action.
                        from .attachments import validate_images
                        images=validate_images(data.get('images'))
                        return self.reply(runtime.steer(text,images=images) if images else runtime.steer(text))
                    if self.path == '/stop':
                        runtime.stop()
                        return self.reply({'stopped':True})
                return self.reply({'error':'Operación no disponible en el celular.'},404)
            except PermissionError as e: self.reply({'error':str(e)},401)
            except (ValueError, TypeError): self.reply({'error':'Solicitud inválida o código vencido.'},400)
            except Exception: self.reply({'error':'No se confirmó la operación. Revisa el PC antes de reenviar.'},503)
    return Handler


def make_mobile_server(runtime, origin, port=0):
    """Loopback harness for integration tests."""
    server = ThreadingHTTPServer(('127.0.0.1', port), mobile_handler(runtime, origin, require_peer=False))
    server.daemon_threads = True
    return server
