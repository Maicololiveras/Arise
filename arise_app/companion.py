"""Least-privilege mobile surface, separate from the privileged desktop bridge.

Bind loopback only and publish this port through Tailscale Serve (never Funnel).
Pairing is initiated on the desktop, bound to one chat, one-use and time limited.
"""
import hashlib
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import threading
import time
from urllib.parse import urlparse


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class Devices:
    def __init__(self, storage):
        self.storage = storage
        with storage.lock, storage.db:
            storage.db.executescript('''
                CREATE TABLE IF NOT EXISTS mobile_pairing(hash TEXT PRIMARY KEY,chat TEXT,expires REAL);
                CREATE TABLE IF NOT EXISTS mobile_devices(id TEXT PRIMARY KEY,chat TEXT,name TEXT,hash TEXT,expires REAL,deadline REAL,revoked INTEGER);
            ''')

    def invite(self, chat):
        code = secrets.token_urlsafe(24)
        with self.storage.lock, self.storage.db:
            self.storage.db.execute("DELETE FROM mobile_pairing WHERE expires<? OR chat=?", (time.time(), chat))
            self.storage.db.execute("INSERT INTO mobile_pairing VALUES(?,?,?)", (digest(code), chat, time.time()+300))
        return {"code": code, "expires_in": 300, "chat": chat}

    def pair(self, code, name):
        if not isinstance(code, str) or len(code)>200 or not isinstance(name, str) or not 1<=len(name)<=80: raise ValueError("Vinculación inválida.")
        with self.storage.lock, self.storage.db:
            row = self.storage.db.execute("SELECT * FROM mobile_pairing WHERE hash=? AND expires>?", (digest(code), time.time())).fetchone()
            if not row: raise ValueError("Código usado o vencido. Genera otro en el PC.")
            self.storage.db.execute("DELETE FROM mobile_pairing WHERE hash=?", (digest(code),))
            identity, token = secrets.token_hex(16), secrets.token_urlsafe(32)
            self.storage.db.execute("INSERT INTO mobile_devices VALUES(?,?,?,?,?,?,0)", (identity, row['chat'], name, digest(token), time.time()+900, time.time()+30*86400))
            return token

    def authorize(self, token):
        if not isinstance(token, str) or len(token)>200: raise PermissionError("Dispositivo no autorizado.")
        with self.storage.lock:
            row = self.storage.db.execute("SELECT id,chat,name FROM mobile_devices WHERE hash=? AND revoked=0 AND expires>? AND deadline>?", (digest(token), time.time(), time.time())).fetchone()
            if not row: raise PermissionError("Sesión vencida o revocada. Vincula nuevamente desde el PC.")
            return dict(row)

    def rotate(self, token):
        with self.storage.lock, self.storage.db:
            self.authorize(token)
            fresh = secrets.token_urlsafe(32)
            self.storage.db.execute("UPDATE mobile_devices SET hash=?,expires=MIN(?,deadline) WHERE hash=?", (digest(fresh), time.time()+900, digest(token)))
            return fresh

    def list(self, chat):
        with self.storage.lock:
            return [dict(r) for r in self.storage.db.execute("SELECT id,name,expires,deadline,revoked FROM mobile_devices WHERE chat=?", (chat,))]

    def revoke(self, chat, identity):
        with self.storage.lock, self.storage.db:
            self.storage.db.execute("UPDATE mobile_devices SET revoked=1 WHERE chat=? AND id=?", (chat, identity))


def make_mobile_server(runtime, origin, port=0):
    parsed = urlparse(origin)
    if parsed.scheme != 'https' or not (parsed.hostname or '').endswith('.ts.net') or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.port:
        raise ValueError("Configura el origen HTTPS exacto de Tailscale, sin ruta ni puerto.")
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_): pass

        def reply(self, body, code=200, cookie=None, mime='application/json'):
            raw = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
            self.send_response(code)
            for k,v in {'Content-Type': mime, 'Content-Length': str(len(raw)), 'Cache-Control': 'no-store',
                        'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer',
                        'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"}.items(): self.send_header(k,v)
            if cookie: self.send_header('Set-Cookie', f'arise_device={cookie}; Secure; HttpOnly; SameSite=Strict; Path=/; Max-Age=900')
            self.end_headers(); self.wfile.write(raw)

        def context(self):
            cookies = SimpleCookie(self.headers.get('Cookie', ''))
            token = cookies['arise_device'].value if 'arise_device' in cookies else ''
            return token, runtime.devices.authorize(token)

        def do_GET(self):
            try:
                if self.path in ('/', '/companion.js', '/companion.css'):
                    name = {'/':'companion.html', '/companion.js':'companion.js', '/companion.css':'companion.css'}[self.path]
                    mime = {'/':'text/html; charset=utf-8', '/companion.js':'text/javascript', '/companion.css':'text/css'}[self.path]
                    return self.reply((Path(__file__).parent/'resources'/name).read_bytes(), mime=mime)
                token, device = self.context()
                if self.path != '/messages': return self.reply({'error':'Ruta no disponible.'},404)
                messages = runtime.storage.messages(device['chat'])[-100:]
                return self.reply({'chat':device['chat'], 'active':runtime.conversation==device['chat'],
                                   'messages':[{k:m[k] for k in ('id','role','text','created')} for m in messages]})
            except PermissionError as e: self.reply({'error':str(e)},401)

        def do_POST(self):
            try:
                # Browser requests are same-origin only; the desktop bridge stays inaccessible.
                if self.headers.get('Origin') != origin: return self.reply({'error':'Origen no autorizado.'},403)
                if self.headers.get('Content-Type') != 'application/json': return self.reply({'error':'Se requiere JSON.'},415)
                self.connection.settimeout(5)
                length = int(self.headers.get('Content-Length','0'))
                if not 0<length<=40000: raise ValueError('Mensaje demasiado grande.')
                data = json.loads(self.rfile.read(length))
                if not isinstance(data,dict): raise ValueError('JSON inválido.')
                if self.path == '/pair':
                    return self.reply({'paired':True},cookie=runtime.devices.pair(data.get('code'),data.get('name')))
                token, device = self.context()
                if self.path == '/renew': return self.reply({'renewed':True},cookie=runtime.devices.rotate(token))
                with runtime.transition_lock:
                    runtime.devices.authorize(token)
                    if runtime.conversation != device['chat']: return self.reply({'error':'Abre este chat en el PC para enviar o detener. El historial sigue disponible.'},409)
                    if self.path == '/prompt':
                        text = data.get('text')
                        if not isinstance(text,str) or not 0<len(text.strip())<=12000: raise ValueError('Texto inválido.')
                        # Existing permissions and approval UI still govern every action.
                        return self.reply(runtime.steer(text))
                    if self.path == '/stop':
                        runtime.stop()
                        return self.reply({'stopped':True})
                return self.reply({'error':'Operación no disponible en el celular.'},404)
            except PermissionError as e: self.reply({'error':str(e)},401)
            except (ValueError, TypeError): self.reply({'error':'Solicitud inválida o código vencido.'},400)
            except Exception: self.reply({'error':'No se confirmó la operación. Revisa el PC antes de reenviar.'},503)
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    return server
