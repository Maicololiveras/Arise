"""Install the user's private hands/eyes without copying their sources into ARISE."""
import json
import os
import shutil
import subprocess
import tempfile
import threading
import tomllib
import urllib.request
import uuid
from pathlib import Path
from .github_access import github_token, github_opener, github_json
from .downloads import safe_extract
from .bundle import application_root
from .processes import executable_argv
from .discovery import command_available
from .diagnostics import checked_run
LOCK=threading.Lock()
COMPONENTS={'screenview':('screenview-mcp','screenview_mcp.server:main'),'inputcontrol':('inputcontrol-mcp','inputcontrol_mcp.server:main'),'transcripcion':('transcripcion-ia','transcripcion_mcp.server:main')}

def setup_desktop_tools(runtime):
    if os.name!='nt': raise RuntimeError('Manos y ojos requieren Windows para instalarse desde ARISE.')
    if not LOCK.acquire(blocking=False): raise RuntimeError('La instalación de manos y ojos ya está en curso.')
    try:
        with runtime.transition_lock:
            if runtime.busy: raise RuntimeError('Detén la tarea activa antes de instalar dependencias.')
            if getattr(runtime,'voice_service',None): runtime.voice_service.end_session()
            return _install(runtime)
    finally: LOCK.release()

def _install(runtime):
    # Never pip-install over DLLs held by the currently running MCP processes.
    parent=runtime.storage.root/'tools';parent.mkdir(exist_ok=True)
    tools=parent/('runtime-'+uuid.uuid4().hex);tools.mkdir()
    try:
        result=_install_into(runtime,tools)
        # Informational marker only; a marker write must not remove an active runtime.
        try: (parent/'installed.json').write_text(json.dumps(result['components'],indent=2),encoding='utf-8')
        except OSError: pass
        return result
    except Exception:
        shutil.rmtree(tools,ignore_errors=True)
        raise

def _install_into(runtime,tools):
    token=github_token(runtime.credentials)
    if not token: raise RuntimeError('Conecta GitHub una vez para descargar tus repositorios privados de manos y ojos.')
    opener=github_opener(token); bundle=application_root()/'bundle'
    python=tools/'python'; source_python=bundle/'python'
    if not source_python.is_dir(): raise RuntimeError('Este instalador no incluye el runtime de herramientas. Instala ARISE 0.4.0 o posterior.')
    if not (python/'python.exe').is_file(): shutil.copytree(source_python,python,dirs_exist_ok=True)
    launcher=tools/'mcp_entry.py'; shutil.copy2(bundle/'mcp_entry.py',launcher)
    if (bundle/'media').is_dir(): shutil.copytree(bundle/'media',tools/'media',dirs_exist_ok=True)
    records={}; packages=[]; build_requirements=set()
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
            metadata=tomllib.loads((roots[0]/'pyproject.toml').read_text(encoding='utf-8'))
            requirements=metadata.get('build-system',{}).get('requires',['setuptools','wheel'])
            if not isinstance(requirements,list) or not all(isinstance(item,str) and item and not item.startswith('-') for item in requirements):
                raise RuntimeError('Requisitos de compilación inválidos en el repositorio de herramientas.')
            build_requirements.update(requirements)
            packages.append(str(roots[0])+('[local]' if name=='transcripcion' else '[windows]')); records[name]={'repo':repo,'commit':commit,'entry':entry}
        command=[str(python/'python.exe'),'-m','pip','install','--disable-pip-version-check','--no-warn-script-location','--no-build-isolation',*packages]
        env={key:value for key,value in os.environ.items() if key not in ('GITHUB_TOKEN','GH_TOKEN','OPENAI_API_KEY','ANTHROPIC_API_KEY','GEMINI_API_KEY')}
        env['PYTHONPATH']=''
        # Embedded Python's _pth ignores pip's isolated-build PYTHONPATH. Install
        # declared build backends into the owned runtime before building sources.
        if build_requirements:
            checked_run([str(python/'python.exe'),'-m','pip','install','--disable-pip-version-check',*sorted(build_requirements)], 'Preparación de compilación de herramientas', env=env, timeout=480, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        checked_run(command, 'Instalación de manos y ojos', env=env, timeout=480, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    probe=subprocess.run([str(python/'python.exe'),'-c','import screenview_mcp.server, inputcontrol_mcp.server, transcripcion_mcp.server'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if probe.returncode: raise RuntimeError('Las herramientas descargadas no pudieron cargarse; no se cambió la configuración.')
    forge_spec,forge_record=install_forge(bundle,tools,opener)
    for name in (*COMPONENTS,'forge'):
        old=runtime.mcp.pop(name,None)
        if old: old.close()
    specs={name:{'command':[str(python/'python.exe'),str(launcher),record['entry']],'enabled':True} for name,record in records.items()}
    specs['forge']=forge_spec;records['forge']=forge_record
    previous=json.loads(json.dumps(runtime.storage.config['mcp']))
    for name,spec in specs.items():
        spec['enabled']=previous.get(name,{}).get('enabled',True)
    runtime.settings({'mcp':{**previous,**specs}})
    try:
        catalogs={name:len(runtime.connect_mcp(name).tools) for name in specs if specs[name]['enabled']}
        if not all(catalogs.values()): raise RuntimeError('Uno de los catálogos MCP está vacío.')
    except Exception:
        runtime.settings({'mcp':previous})
        raise
    try: (tools/'installed.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    except OSError: pass
    runtime.emit('tools_configured',{'mcp':specs,'catalogs':catalogs})
    runtime.emit('notice',{'text':'Herramientas instaladas: pantalla, control, transcripción y Forge. Catálogos MCP verificados.'})
    return {'installed':True,'catalogs':catalogs,'components':records}

def install_forge(bundle, tools, opener):
    """Build the user's private Forge with the shipped Node/npm, never global npm."""
    import uuid
    node=bundle/'node/node.exe'
    npm=bundle/'node/node_modules/npm/bin/npm-cli.js'
    if not node.is_file() or not npm.is_file():
        raise RuntimeError('Falta Node/npm integrado para Forge. Usa el nuevo ZIP completo de ARISE.')
    base='https://api.github.com/repos/Maicololiveras/forge-mcp'
    # Pin the reviewed voice-capable build; never install an older default-branch Forge.
    commit='a1fc2f440c6b3c5288838bbe9fc5e2f1ad3ba6c5'
    destination=tools/('forge-'+uuid.uuid4().hex)
    try:
        with tempfile.TemporaryDirectory(dir=tools,prefix='forge-source-') as temporary:
            archive=Path(temporary)/'forge.zip';total=0
            with opener(base+'/zipball/'+commit,timeout=30) as response,archive.open('wb') as output:
                while block:=response.read(1024*1024):
                    total+=len(block)
                    if total>100_000_000:raise RuntimeError('Forge supera el límite de descarga.')
                    output.write(block)
            extracted=Path(temporary)/'source';safe_extract(archive,extracted)
            roots=[p for p in extracted.iterdir() if p.is_dir() and (p/'package.json').is_file()]
            if len(roots)!=1:raise RuntimeError('La descarga no contiene Forge.')
            shutil.move(str(roots[0]),str(destination))
        env={key:value for key,value in os.environ.items() if key not in ('GITHUB_TOKEN','GH_TOKEN','OPENAI_API_KEY','ANTHROPIC_API_KEY','GEMINI_API_KEY')}
        env['PATH']=str(node.parent)+os.pathsep+env.get('PATH','')
        for arguments,label in ((['ci','--ignore-scripts','--no-audit','--no-fund'],'Dependencias de Forge'),(['run','build'],'Compilación de Forge')):
            checked_run([str(node),str(npm),*arguments],label,cwd=str(destination),env=env,timeout=600,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        entry=destination/'dist/bin/forge-mcp-cli.js'
        if not entry.is_file():raise RuntimeError('Forge no generó su ejecutable MCP.')
        return {'command':[str(node),str(entry)],'enabled':True},{'repo':'forge-mcp','commit':commit}
    except Exception:
        shutil.rmtree(destination,ignore_errors=True)
        raise


def auto_setup(runtime):
    if os.name!='nt': return
    # A previous marker is not proof that dependencies still exist.
    missing=[name for name in (*COMPONENTS,'forge')
             if runtime.storage.config['mcp'].get(name,{}).get('enabled',True)
             and not command_available(runtime.storage.config['mcp'].get(name,{}).get('command'))]
    if runtime.storage.config['mcp'].get('forge',{}).get('enabled',True):
        from .forge_voice import voice_command
        try:voice_command(runtime)
        except RuntimeError:
            if 'forge' not in missing:missing.append('forge')
    if not missing:return
    if not github_token(runtime.credentials):
        runtime.emit('notice',{'text':'Faltan herramientas privadas: '+', '.join(missing)+'. Conecta GitHub para instalarlas con sus dependencias.'});return
    try:
        with runtime.transition_lock:
            if runtime.busy:return
            runtime.emit('notice',{'text':'Instalando herramientas y dependencias que faltan…'})
            setup_desktop_tools(runtime)
    except Exception as error:runtime.emit('notice',{'text':str(error)[:300]})
