"""Optional text browser access. Bind loopback; use a TLS reverse proxy or Tailscale."""
import argparse
import hmac
import json
import os
import secrets
import threading
import time
import urllib.parse
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from .remote import RemoteAssistant
from .daemon import ensure_daemon

LOGIN=b'''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>ARISE</title><body style="background:#0A1828;color:#EDF8FF;font:16px system-ui;display:grid;place-items:center;height:90vh"><form method="post" action="/login"><h1 style="color:#74F6FF">ARISE</h1><p>Acceso privado al asistente</p><input name="password" type="password" placeholder="Clave de acceso" required autocomplete="current-password"><button>Entrar</button></form></body></html>'''

def make_gateway(remote,password,public_origin,port=8766):
    if len(password)<16:raise ValueError("La clave remota debe tener al menos 16 caracteres")
    origin=urllib.parse.urlparse(public_origin)
    if origin.scheme not in ('https','http') or not origin.netloc:raise ValueError('Origen público inválido')
    if origin.scheme=='http' and origin.hostname not in ('127.0.0.1','localhost'):raise ValueError('El acceso remoto requiere HTTPS')
    sessions={};failed={};lock=threading.RLock();root=Path(__file__).resolve().parents[1]/'web'
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_):pass
        def response(self,body,code=200,mime='application/json',cookie=None):
            data=json.dumps(body,ensure_ascii=False).encode() if mime=='application/json' else body
            self.send_response(code);self.send_header('Content-Type',mime+'; charset=utf-8');self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            if cookie:self.send_header('Set-Cookie',cookie)
            self.end_headers();self.wfile.write(data)
        def valid_host(self):
            if self.headers.get('Host')!=origin.netloc:self.response({'error':'Host no autorizado'},403);return False
            return True
        def session(self):
            try:
                cookie=SimpleCookie(self.headers.get('Cookie',''));identity=cookie['arise_session'].value
                with lock:
                    value=sessions.get(identity)
                    if value and value['expires']>time.time():return value
            except (KeyError,ValueError):pass
            return None
        def do_GET(self):
            if not self.valid_host():return
            session=self.session();parsed=urllib.parse.urlparse(self.path)
            if parsed.path=='/' and not session:self.response(LOGIN,mime='text/html');return
            if not session:self.response({'error':'Inicia sesión'},401);return
            try:
                if parsed.path=='/':self.response((root/'index.html').read_bytes(),mime='text/html')
                elif parsed.path in ('/app.js','/style.css'):
                    self.response((root/parsed.path[1:]).read_bytes(),mime='text/javascript' if parsed.path.endswith('.js') else 'text/css')
                elif parsed.path=='/api/session':self.response({'csrf':session['csrf']})
                elif parsed.path=='/api/messages':self.response(remote.request('messages'))
                elif parsed.path=='/api/status':self.response(remote.status())
                elif parsed.path=='/api/events':
                    cursor=int(urllib.parse.parse_qs(parsed.query).get('after',[0])[0]);self.response(remote.events_after(cursor))
                else:self.response({'error':'Ruta desconocida'},404)
            except Exception:self.response({'error':'El asistente no está disponible'},503)
        def do_POST(self):
            if not self.valid_host():return
            if self.headers.get('Origin')!=public_origin:self.response({'error':'Origen no autorizado'},403);return
            self.connection.settimeout(10)
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<50000:raise ValueError('Solicitud inválida')
                raw=self.rfile.read(length)
                if self.path=='/login':
                    now=time.monotonic();address=self.client_address[0]
                    with lock:
                        attempts=[t for t in failed.get(address,[]) if now-t<60]
                        if len(attempts)>=5:self.response({'error':'Espera un minuto antes de reintentar'},429);return
                        entered=urllib.parse.parse_qs(raw.decode()).get('password',[''])[0]
                        if not hmac.compare_digest(entered.encode(),password.encode()):
                            failed[address]=attempts+[now];self.response(LOGIN,401,'text/html');return
                        identity=secrets.token_urlsafe(32)
                        if len(sessions)>100:sessions.clear()
                        sessions[identity]={'csrf':secrets.token_urlsafe(32),'expires':time.time()+3600}
                    self.send_response(303);self.send_header('Location','/');self.send_header('Set-Cookie','arise_session='+identity+'; HttpOnly; SameSite=Strict; Path=/; Max-Age=3600'+('; Secure' if origin.scheme=='https' else ''));self.end_headers();return
                session=self.session()
                if not session:self.response({'error':'Inicia sesión'},401);return
                if not hmac.compare_digest(self.headers.get('X-CSRF',''),session['csrf']):self.response({'error':'Solicitud no autorizada'},403);return
                data=json.loads(raw)
                if self.path=='/api/prompt':value=remote.steer(data['text'])
                elif self.path=='/api/stop':value=remote.stop()
                elif self.path=='/api/approval':remote.approve(data['id'],data.get('approved'));value={'ok':True}
                else:self.response({'error':'Ruta desconocida'},404);return
                self.response(value)
            except Exception:self.response({'error':'No se pudo completar la operación'},400)
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler);server.daemon_threads=True;return server

def main():
    p=argparse.ArgumentParser(description='ARISE optional private browser gateway')
    p.add_argument('--data-dir',required=True);p.add_argument('--port',type=int,default=8766);p.add_argument('--public-origin',required=True)
    args=p.parse_args();password=os.environ.get('ARISE_REMOTE_PASSWORD','')
    remote=RemoteAssistant(ensure_daemon(args.data_dir),args.data_dir)
    server=make_gateway(remote,password,args.public_origin,args.port)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=='__main__':main()
