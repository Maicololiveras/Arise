"""Real Windows install-over-running-app test; user data and chats must survive."""
import json
import os
import psutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from arise_app.daemon import read_descriptor,ping
from arise_app.remote import RemoteAssistant
from arise_app.storage import DEFAULTS
from arise_app import __version__

setup=Path('dist/ARISE-Setup.exe').resolve()
if os.name!='nt':raise RuntimeError('Installer smoke requires Windows')
report={}
diagnostics=Path('artifacts/installer-diagnostics').resolve()
diagnostics.mkdir(parents=True,exist_ok=True)
setup_attempt=0
with tempfile.TemporaryDirectory(prefix='arise-upgrade-',ignore_cleanup_errors=True) as temporary:
    root=Path(temporary); install=root/'Installed ARISE'; data=root/'data'; data.mkdir()
    config={**DEFAULTS,'onboarding_complete':True,'wake_enabled':False,'workspace':str(root/'Workspace'),'pi_command':[str(install/'bundle/node/node.exe'),str(install/'bundle/node/node_modules/@earendil-works/pi-coding-agent/dist/cli.js')],'gentle_path':str(install/'bundle/node/node_modules/gentle-pi')}
    (data/'settings.json').write_text(json.dumps(config),encoding='utf-8')
    agent=root/'agent';agent.mkdir()
    (agent/'settings.json').write_text(json.dumps({'packages':[],'telemetry':False}),encoding='utf-8')
    (agent/'models.json').write_text(json.dumps({'providers':{'arise-smoke':{'baseUrl':'http://127.0.0.1:1/v1','api':'openai-completions','apiKey':'fixture-only','models':[{'id':'fixture','input':['text'],'contextWindow':32000,'maxTokens':1000}]}}}),encoding='utf-8')
    env={**os.environ,'PI_CODING_AGENT_DIR':str(agent),'PI_OFFLINE':'1','QT_QPA_PLATFORM':'offscreen','ARISE_SKIP_NETWORK_SETUP':'1'}
    def run_setup():
        global setup_attempt
        setup_attempt+=1
        log=diagnostics/f'setup-{setup_attempt}.log'
        print(f'Installer attempt {setup_attempt}: starting',flush=True)
        # Keep the installed UI/daemon running, but do not open the interactive
        # Gentle provisioning wizard while testing the bundled Pi fixture.
        command=[str(setup),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-',
            '/ARISE-SETUP=0',f'/DIR={install}',f'/ARISE-DATA={data}',f'/LOG={log}']
        process=subprocess.Popen(command,env=env)
        try:
            code=process.wait(timeout=600)
        except subprocess.TimeoutExpired:
            # Inno has a bootstrap parent and a child holding setup.log/files.
            # Kill only this test's installer tree before temporary cleanup.
            parent=psutil.Process(process.pid)
            children=parent.children(recursive=True)
            for child in reversed(children):
                try:child.kill()
                except psutil.NoSuchProcess:pass
            process.kill();process.wait(timeout=15)
            psutil.wait_procs(children,timeout=15)
            raise
        finally:
            if log.exists():print(log.read_text(errors='replace')[-6000:],flush=True)
            stop_log=data/'installer-stop.log'
            if stop_log.exists():
                text=stop_log.read_text(errors='replace')
                (diagnostics/f'stop-{setup_attempt}.log').write_text(text,encoding='utf-8')
                print(text[-6000:],flush=True)
        if code:raise RuntimeError('Installer failed: '+str(code))
        print(f'Installer attempt {setup_attempt}: completed',flush=True)
    def ready(previous_pid=None):
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            descriptor=read_descriptor(data)
            if descriptor and descriptor['pid']!=previous_pid and ping(descriptor):return descriptor
            time.sleep(.2)
        raise RuntimeError('Post-install ARISE did not start')
    def stop():
        engine=install/'ARISE.exe'
        if engine.is_file():subprocess.run([str(engine),'--shutdown','--data-dir',str(data)],env=env,timeout=45)
    try:
        run_setup();descriptor=ready();remote=RemoteAssistant(descriptor,data)
        icon=install/f'arise-{__version__}.ico'
        if not icon.is_file() or icon.read_bytes()!=Path('artifacts/arise.ico').read_bytes():
            raise RuntimeError('Installed orb icon does not match the packaged brand')
        import win32com.client
        shortcut=Path(os.environ['APPDATA'])/'Microsoft/Windows/Start Menu/Programs/ARISE/ARISE.lnk'
        icon_location=win32com.client.Dispatch('WScript.Shell').CreateShortCut(str(shortcut)).IconLocation
        shortcut_icon=Path(icon_location.rsplit(',',1)[0].strip('"'))
        if not shortcut.is_file() or not shortcut_icon.is_file() or not os.path.samefile(shortcut_icon,icon):
            raise RuntimeError('Start menu shortcut does not reference the versioned orb icon')
        remote.settings({'agent_provider':'arise-smoke','agent_model':'fixture','thinking':'off','pi_extra_args':['--offline','--no-extensions','--no-skills','--no-context-files']})
        if not remote.connect_pi().get('gentleVerified'):raise RuntimeError('Installed Pi/Gentle unavailable')
        remote.call_tool('memory.save',{'text':'Survives installer replacement'})
        word=json.loads(remote.call_tool('documents.create_docx',{'path':'installer-smoke.docx','title':'QA Word','paragraphs':['DOCX created by the installed frozen runtime.']})['content'][0]['text'])
        if not word.get('content_verified'):raise RuntimeError('Installed DOCX generation was not verified')
        old_daemon=psutil.Process(descriptor['pid']);old_children=old_daemon.children(recursive=True)
        old_ui=[p for p in psutil.process_iter(['exe']) if p.info['exe'] and Path(p.info['exe']).name.lower()=='arise.exe' and os.path.samefile(p.info['exe'],install/'ARISE.exe') and p.pid!=descriptor['pid']]
        if not old_ui:raise RuntimeError('Installed UI was not captured for replacement validation')
        chat=install/'chat/chat-keeper/keep.txt';chat.parent.mkdir(parents=True,exist_ok=True);chat.write_text('do not delete',encoding='utf-8')
        obsolete=install/'_internal/arise-obsolete.txt';obsolete.write_text('stale managed file')
        run_setup();new=ready(descriptor['pid']);new_remote=RemoteAssistant(new,data)
        for process in [old_daemon,*old_children,*old_ui]:
            if process.is_running():raise RuntimeError('Old owned process survived replacement: '+str(process.pid))
        if chat.read_text()!='do not delete' or obsolete.exists():raise RuntimeError('Installer data preservation/managed cleanup failed')
        word_read=json.loads(new_remote.call_tool('documents.read_docx',{'path':'installer-smoke.docx'})['content'][0]['text'])
        if 'DOCX created by the installed frozen runtime.' not in word_read['text']:raise RuntimeError('DOCX content did not survive installer replacement')
        notes=json.loads(new_remote.call_tool('memory.search',{'query':'Survives'})['content'][0]['text'])['notes']
        if not notes or new_remote.status()['version']!=__version__:raise RuntimeError('Version or persisted memory incorrect')
        if not (install/'bundle/python/python.exe').is_file():raise RuntimeError('Missing runtime for private tools')
        report={'installed_docx_generation_and_preservation':'passed','versioned_shortcut_icon':'passed','fresh_install':'passed','replace_running_ui_daemon_pi':'passed','owned_children_closed':len(old_children),'user_chat_preserved':'passed','memory_preserved':'passed','stale_managed_file_removed':'passed','restarted_version':__version__}
    except Exception as error:
        report['error']=str(error)
        Path('artifacts/installer-upgrade.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        raise
    finally:stop()
Path('artifacts/installer-upgrade.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
