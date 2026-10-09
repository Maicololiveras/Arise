"""Install the user's private hands/eyes without copying their sources into ARISE."""
import json
import os
import shutil
import subprocess
import tempfile
import threading
import urllib.request
from pathlib import Path
from .github_access import github_token, github_opener, github_json
from .downloads import safe_extract
from .bundle import application_root
from .processes import executable_argv
LOCK=threading.Lock()
COMPONENTS={'screenview':('screenview-mcp','screenview_mcp.server:main'),'inputcontrol':('inputcontrol-mcp','inputcontrol_mcp.server:main')}

def setup_desktop_tools(runtime):
    if os.name!='nt': raise RuntimeError('Manos y ojos requieren Windows para instalarse desde ARISE.')
    if not LOCK.acquire(blocking=False): raise RuntimeError('La instalación de manos y ojos ya está en curso.')
    try:
        return _install(runtime)
    finally: LOCK.release()

def _install(runtime):
    token=github_token(runtime.credentials)
    if not token: raise RuntimeError('Conecta GitHub una vez para descargar tus repositorios privados de manos y ojos.')
    opener=github_opener(token); bundle=application_root()/'bundle'; tools=runtime.storage.root/'tools'; tools.mkdir(exist_ok=True)
    python=tools/'python'; source_python=bundle/'python'
    if not source_python.is_dir(): raise RuntimeError('Este instalador no incluye el runtime de herramientas. Instala ARISE 0.4.0 o posterior.')
    if not (python/'python.exe').is_file(): shutil.copytree(source_python,python,dirs_exist_ok=True)
    launcher=tools/'mcp_entry.py'; shutil.copy2(bundle/'mcp_entry.py',launcher)
    if (bundle/'media').is_dir(): shutil.copytree(bundle/'media',tools/'media',dirs_exist_ok=True)
    records={}; packages=[]
    with tempfile.TemporaryDirectory(dir=tools,prefix='sources-') as temporary:
        for name,(repo,entry) in COMPONENTS.items():
            base='https://api.github.com/repos/Maicololiveras/'+repo
            metadata=github_json(base,opener); branch=metadata['default_branch']
            commit=github_json(base+'/commits/'+branch,opener)['sha']
            archive=Path(temporary)/(repo+'.zip'); total=0
            with opener(base+'/zipball/'+commit,timeout=30) as response,archive.open('wb') as output:
                while True:
                    block=response.read(1024*1024)
                    if not block: break
                    total+=len(block)
                    if total>100_000_000: raise RuntimeError('El repositorio de herramientas supera el límite de descarga.')
                    output.write(block)
            extracted=Path(temporary)/repo; safe_extract(archive,extracted)
            roots=[path for path in extracted.iterdir() if path.is_dir() and (path/'pyproject.toml').is_file()]
            if len(roots)!=1: raise RuntimeError('La descarga no contiene el proyecto Python esperado.')
            packages.append(str(roots[0])+'[windows]'); records[name]={'repo':repo,'commit':commit,'entry':entry}
        command=[str(python/'python.exe'),'-m','pip','install','--disable-pip-version-check','--no-warn-script-location',*packages]
        env={key:value for key,value in os.environ.items() if key not in ('GITHUB_TOKEN','GH_TOKEN','OPENAI_API_KEY','ANTHROPIC_API_KEY','GEMINI_API_KEY')}
        env['PYTHONPATH']=''
        result=subprocess.run(command,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=480,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if result.returncode: raise RuntimeError('No se pudieron instalar las dependencias de manos y ojos. Revisa la conexión y vuelve a intentar.')
    probe=subprocess.run([str(python/'python.exe'),'-c','import screenview_mcp.server, inputcontrol_mcp.server'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if probe.returncode: raise RuntimeError('Las herramientas descargadas no pudieron cargarse; no se cambió la configuración.')
    for name in COMPONENTS:
        old=runtime.mcp.pop(name,None)
        if old: old.close()
    specs={name:{'command':[str(python/'python.exe'),str(launcher),record['entry']],'enabled':True} for name,record in records.items()}
    runtime.settings({'mcp':{**runtime.storage.config['mcp'],**specs}})
    catalogs={name:len(runtime.connect_mcp(name).tools) for name in COMPONENTS}
    if not all(catalogs.values()): raise RuntimeError('Uno de los catálogos MCP está vacío.')
    (tools/'installed.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    runtime.emit('tools_configured',{'mcp':specs,'catalogs':catalogs})
    runtime.emit('notice',{'text':'Manos y ojos instalados, configurados y con catálogo MCP verificado.'})
    return {'installed':True,'catalogs':catalogs,'components':records}

def auto_setup(runtime):
    if os.name!='nt' or (runtime.storage.root/'tools/installed.json').is_file(): return
    if not github_token(runtime.credentials):
        runtime.emit('notice',{'text':'Para descargar manos y ojos privados, conecta GitHub en Credenciales y pulsa Instalar y configurar manos y ojos.'}); return
    missing=[]
    for name in COMPONENTS:
        try: executable_argv(runtime.storage.config['mcp'][name]['command'])
        except (ValueError,RuntimeError,KeyError): missing.append(name)
    if missing:
        try: setup_desktop_tools(runtime)
        except Exception as error: runtime.emit('notice',{'text':str(error)[:300]})
