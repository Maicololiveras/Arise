"""App-owned tailnet node. Mobile HTTP travels over child pipes only."""
import io
import json
import os
import queue
import re
import struct
import subprocess
import threading

from .bundle import application_root
from .companion import mobile_handler


def binary():
    return application_root() / 'bundle' / ('arise-tailnode.exe' if os.name == 'nt' else 'arise-tailnode')


def read_settings(runtime):
    path = runtime.storage.root / 'mobile-server.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def save_settings(runtime, value):
    path = runtime.storage.root / 'mobile-server.json'
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value), encoding='utf-8')
    os.replace(temp, path)


class TailNode:
    def __init__(self, runtime, key):
        directory = runtime.storage.root / 'tailnode'
        directory.mkdir(mode=0o700, exist_ok=True)
        env = {name: os.environ[name] for name in ('HOME','USERPROFILE','SystemRoot','WINDIR','LOCALAPPDATA',
                'APPDATA','TMPDIR','TMP','TEMP','LANG','PATH','SSL_CERT_FILE','SSL_CERT_DIR') if name in os.environ}
        env['TS_NO_LOGS_NO_SUPPORT'] = 'true'
        self.process = subprocess.Popen([str(binary())], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL, env=env, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            self.process.stdin.write((json.dumps({'Dir':str(directory.resolve()), 'Key':key})+'\n').encode())
            self.process.stdin.flush()
            ready = queue.Queue(1)
            threading.Thread(target=lambda: ready.put(self.process.stdout.readline(256)), daemon=True).start()
            dns = ready.get(timeout=105).decode('ascii').strip()
            if not re.fullmatch(r'[a-z0-9-]+\.[a-z0-9.-]+\.ts\.net', dns):
                raise RuntimeError('Comprueba la clave de un solo uso con etiqueta tag:arise-mobile, MagicDNS, HTTPS y la aprobación del dispositivo en Tailscale.')
            self.origin = 'https://' + dns
            self.handler = mobile_handler(runtime, self.origin)
            threading.Thread(target=self.serve, daemon=True).start()
        except BaseException:
            self.close()
            raise

    def serve(self):
        # The Go listener normalizes and bounds each complete request before writing.
        process = self.process
        class PipeHandler(self.handler):
            def setup(self):
                self.rfile, self.wfile, self.connection = self.request, process.stdin, None
            def finish(self):
                self.wfile.flush()
        try:
            while process.poll() is None:
                header = process.stdout.read(4)
                if len(header) != 4:
                    break
                length, = struct.unpack('!I', header)
                if not 0 < length <= 12_030_000:
                    break
                packet = process.stdout.read(length)
                if len(packet) != length:
                    break
                PipeHandler(io.BytesIO(packet), ('tailnet', 0), None)
        except (OSError, ValueError):
            pass
        finally:
            if process.poll() is None:
                process.terminate()

    def close(self):
        if self.process.poll() is None:
            self.process.kill()
        self.process.wait()
        self.process.stdin.close()
        self.process.stdout.close()


def prepare(runtime, key=''):
    if not isinstance(key, str) or len(key) > 1024:
        raise ValueError('Clave de registro inválida.')
    with runtime.mobile_lock:
        if not runtime.mobile_security.enabled():
            raise RuntimeError('Primero confirma el autenticador de ARISE.')
        if not binary().is_file():
            raise RuntimeError('Esta instalación carece de arise-tailnode. Consulta la guía móvil de QA.')
        if runtime.mobile_server and runtime.mobile_server.process.poll() is not None:
            runtime.mobile_server.close()
            runtime.mobile_server = None
        if not runtime.mobile_server:
            saved = read_settings(runtime)
            if not key and saved.get('transport') != 'tsnet':
                raise ValueError('Introduce una clave de registro de un solo uso para el nodo ARISE.')
            node = TailNode(runtime, key)
            try:
                save_settings(runtime, {'transport':'tsnet', 'enabled':True})
            except Exception:
                node.close()
                raise
            runtime.mobile_server = node
            runtime.mobile_origin = node.origin
        return {'ready':True, 'origin':runtime.mobile_origin}


def resume(runtime):
    saved = read_settings(runtime)
    if saved.get('enabled') and saved.get('transport') == 'tsnet':
        prepare(runtime)


def invite(runtime):
    if not runtime.mobile_server or runtime.mobile_server.process.poll() is not None or not runtime.mobile_security.enabled():
        raise RuntimeError('Prepara la conexión privada antes de vincular el chat.')
    from urllib.parse import urlencode
    invitation = runtime.devices.invite(runtime.conversation)
    return {**invitation, 'url':runtime.mobile_origin+'/#'+urlencode({'code':invitation['code']})}


def readiness(runtime):
    installed = binary().is_file()
    secured = runtime.mobile_security.enabled()
    serving = bool(runtime.mobile_server and runtime.mobile_server.process.poll() is None)
    return {'steps':[{'ready':installed,'message':'Componente Tailscale integrado.' if installed else 'Falta arise-tailnode.'},
                     {'ready':secured,'message':'Autenticador confirmado.' if secured else 'Configura el autenticador.'},
                     {'ready':serving,'message':'Nodo conectado.' if serving else 'Prepara el nodo privado.'},
                     {'ready':False,'message':'En el teléfono conecta Tailscale y escanea el QR.'}],
            'ready_to_pair':installed and secured and serving}
