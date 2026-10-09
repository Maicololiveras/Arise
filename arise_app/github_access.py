"""GitHub access for private updates/components; credentials stay in the daemon."""
import json
import os
import shutil
import subprocess
import urllib.request
import urllib.error
from urllib.parse import urlparse

class PrivateRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        if urlparse(new_url).scheme != 'https': raise RuntimeError('GitHub redirigió a una descarga sin HTTPS.')
        redirected=super().redirect_request(request,fp,code,message,headers,new_url)
        if urlparse(new_url).netloc != urlparse(request.full_url).netloc:
            redirected.remove_header('Authorization')
        return redirected

def github_token(credentials):
    token=credentials.get('github-updates')
    if token: return token
    gh=shutil.which('gh')
    if gh:
        result=subprocess.run([gh,'auth','token','--hostname','github.com'],capture_output=True,text=True,timeout=8,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if result.returncode==0: return result.stdout.strip()
    return ''

def github_opener(token=''):
    opener=urllib.request.build_opener(PrivateRedirect())
    def open_request(request,timeout=30):
        if isinstance(request,str): request=urllib.request.Request(request)
        if urlparse(request.full_url).netloc != 'api.github.com': raise ValueError('Las solicitudes autenticadas solo se envían a api.github.com.')
        request.add_header('User-Agent','ARISE Assistant');request.add_header('X-GitHub-Api-Version','2022-11-28')
        if token: request.add_header('Authorization','Bearer '+token)
        try: return opener.open(request,timeout=timeout)
        except urllib.error.HTTPError as error:
            if error.code in (401,403,404): raise RuntimeError('Conecta GitHub en Credenciales con acceso a ARISE y a las herramientas privadas. También puedes usar una sesión de gh auth login.') from None
            raise
    return open_request

def github_json(url,opener):
    with opener(urllib.request.Request(url,headers={'Accept':'application/vnd.github+json'}),timeout=15) as response: return json.load(response)
