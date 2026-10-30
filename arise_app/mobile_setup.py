"""Private Tailscale setup. Existing Serve/Funnel configuration is never overwritten."""
import json
import os
from pathlib import Path
import shutil
import subprocess


def cli(*args):
    binary=shutil.which('tailscale')
    if not binary:
        candidate=Path(os.environ.get('ProgramFiles','C:/Program Files'))/'Tailscale/tailscale.exe'
        if candidate.is_file(): binary=str(candidate)
    if not binary: raise RuntimeError('Instala Tailscale en este PC, inicia sesión y vuelve a pulsar Conectar mi teléfono.')
    result=subprocess.run([binary,*args],capture_output=True,text=True,timeout=45,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:
        raise RuntimeError('Tailscale no completó la configuración. Abre su aplicación, comprueba la sesión y los permisos. '+result.stderr[:400])
    return result.stdout


def prepare(runtime):
    if not runtime.mobile_security.enabled(): raise RuntimeError('Primero configura y confirma el autenticador de ARISE.')
    state=json.loads(cli('status','--json'))
    if state.get('BackendState')!='Running': raise RuntimeError('Abre Tailscale en este PC e inicia sesión con la misma cuenta que usarás en el teléfono.')
    dns=state.get('Self',{}).get('DNSName','').rstrip('.')
    if not dns.endswith('.ts.net'): raise RuntimeError('Tailscale todavía no informa un nombre privado para este equipo.')
    origin='https://'+dns
    serve=json.loads(cli('serve','status','--json') or '{}')
    if serve:
        saved=read_settings(runtime)
        expected=f'http://127.0.0.1:{saved.get("port",0)}'
        handlers=serve.get('Web',{}).get(dns+':443',{}).get('Handlers',{})
        if (not saved.get('enabled') or saved.get('origin')!=origin or
            handlers!={'/':{'Proxy':expected}} or any(serve.get('AllowFunnel',{}).values()) or
            set(serve.get('Web',{}))!={dns+':443'} or set(serve.get('TCP',{}))!={'443'}):
            raise RuntimeError('Tailscale ya publica otros servicios. ARISE no los reemplazará; revisa su configuración antes de conectar.')
    if not runtime.mobile_server:
        runtime.start_mobile(origin,port=read_settings(runtime).get('port',0))
    elif getattr(runtime,'mobile_origin',None)!=origin:
        raise RuntimeError('Detén el acceso móvil anterior antes de cambiar de red.')
    port=runtime.mobile_server.server_port
    try:
        cli('serve','--bg',f'http://127.0.0.1:{port}')
    except Exception:
        runtime.stop_mobile(persist=False)
        raise
    save_settings(runtime,{'enabled':True,'origin':origin,'port':port})
    return {'ready':True,'origin':origin,'message':'Conexión privada preparada. Usa Tailscale en el teléfono y genera la vinculación. El MFA de tu cuenta Tailscale se administra en su proveedor; ARISE no lo ha verificado.'}


def read_settings(runtime):
    path=runtime.storage.root/'mobile-server.json'
    if not path.exists(): return {}
    return json.loads(path.read_text(encoding='utf-8'))


def save_settings(runtime,value):
    path=runtime.storage.root/'mobile-server.json'
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value),encoding='utf-8');os.replace(temp,path)


def resume(runtime):
    value=read_settings(runtime)
    if value.get('enabled'):
        if not runtime.mobile_security.enabled(): raise RuntimeError('Acceso móvil detenido: falta el autenticador.')
        runtime.start_mobile(value['origin'],port=value['port'])


def invite(runtime):
    if not runtime.mobile_server or not runtime.mobile_security.enabled(): raise RuntimeError('Configura el autenticador y conecta el teléfono primero.')
    from urllib.parse import urlencode
    invitation=runtime.devices.invite(runtime.conversation)
    return {**invitation,'url':runtime.mobile_origin+'/#'+urlencode({'code':invitation['code']})}
