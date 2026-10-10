"""GitHub access for private updates/components; credentials stay in the daemon."""
import json
import os
import shutil
import subprocess
import tempfile
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

def gh_executable():
    from .bundle import application_root
    bundled = application_root()/'bundle/gh/gh.exe'
    return str(bundled) if bundled.is_file() else shutil.which('gh')

def github_token(credentials):
    token=credentials.get('github-updates')
    if token: return token
    gh=gh_executable()
    if gh:
        result=subprocess.run([gh,'auth','token','--hostname','github.com'],capture_output=True,text=True,timeout=8,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if result.returncode==0: return result.stdout.strip()
    return ''

def github_opener(token=''):
    opener=urllib.request.build_opener(PrivateRedirect())
    def open_request(request,timeout=30):
        if isinstance(request,str): request=urllib.request.Request(request)
        if urlparse(request.full_url).netloc != 'api.github.com': raise ValueError('Las solicitudes autenticadas solo se envían a api.github.com.')
        gh=gh_executable()
        if gh:
            # gh follows GitHub's archive redirects without forwarding the token
            # to another host. Secrets travel only through its environment.
            env=os.environ.copy()
            if token: env['GH_TOKEN']=token
            env['GH_PROMPT_DISABLED']='1'
            endpoint=request.full_url.removeprefix('https://api.github.com/')
            command=[gh,'api','--hostname','github.com',endpoint]
            for key,value in request.header_items():
                if key.lower()!='authorization':command.extend(['-H',key+': '+value])
            output=tempfile.TemporaryFile()
            try:
                result=subprocess.run(command,env=env,stdout=output,stderr=subprocess.DEVNULL,timeout=max(timeout,120),creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                if result.returncode:raise RuntimeError('gh no pudo descargar el componente. Comprueba la conexion y el acceso de GitHub a los repositorios privados.')
                output.seek(0)
                return output
            except Exception:
                output.close()
                raise
        request.add_header('User-Agent','ARISE Assistant');request.add_header('X-GitHub-Api-Version','2022-11-28')
        if token: request.add_header('Authorization','Bearer '+token)
        try: return opener.open(request,timeout=timeout)
        except urllib.error.HTTPError as error:
            if error.code in (401,403,404): raise RuntimeError('Conecta GitHub en Credenciales con acceso a ARISE y a las herramientas privadas. También puedes usar una sesión de gh auth login.') from None
            raise
    return open_request

def github_json(url,opener):
    with opener(urllib.request.Request(url,headers={'Accept':'application/vnd.github+json'}),timeout=15) as response: return json.load(response)
