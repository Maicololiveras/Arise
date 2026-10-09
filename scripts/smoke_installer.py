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
with tempfile.TemporaryDirectory(prefix='arise-upgrade-') as temporary:
    root=Path(temporary); install=root/'Installed ARISE'; data=root/'data'; data.mkdir()
    config={**DEFAULTS,'onboarding_complete':True,'wake_enabled':False,'workspace':str(root/'Workspace'),'pi_command':[str(install/'bundle/node/node.exe'),str(install/'bundle/node/node_modules/@earendil-works/pi-coding-agent/dist/cli.js')],'gentle_path':str(install/'bundle/node/node_modules/gentle-pi')}
    (data/'settings.json').write_text(json.dumps(config),encoding='utf-8')
    agent=root/'agent';agent.mkdir()
    (agent/'settings.json').write_text(json.dumps({'packages':[],'telemetry':False}),encoding='utf-8')
    (agent/'models.json').write_text(json.dumps({'providers':{'arise-smoke':{'baseUrl':'http://127.0.0.1:1/v1','api':'openai-completions','apiKey':'fixture-only','models':[{'id':'fixture','input':['text'],'contextWindow':32000,'maxTokens':1000}]}}}),encoding='utf-8')
    env={**os.environ,'PI_CODING_AGENT_DIR':str(agent),'PI_OFFLINE':'1','QT_QPA_PLATFORM':'offscreen','ARISE_SKIP_NETWORK_SETUP':'1'}
    def run_setup():
        result=subprocess.run([str(setup),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-',f'/DIR={install}',f'/ARISE-DATA={data}',f'/LOG={root / "setup.log"}'],env=env,timeout=240)
        if result.returncode:raise RuntimeError('Installer failed: '+str(result.returncode)+' '+(root/'setup.log').read_text(errors='replace')[-4000:])
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
        remote.settings({'agent_provider':'arise-smoke','agent_model':'fixture','thinking':'off','pi_extra_args':['--offline','--no-extensions','--no-skills','--no-context-files']})
        if not remote.connect_pi().get('gentleVerified'):raise RuntimeError('Installed Pi/Gentle unavailable')
        remote.call_tool('memory.save',{'text':'Survives installer replacement'})
        old_daemon=psutil.Process(descriptor['pid']);old_children=old_daemon.children(recursive=True)
        old_ui=[p for p in psutil.process_iter(['exe']) if p.info['exe'] and Path(p.info['exe'])==install/'ARISE.exe' and p.pid!=descriptor['pid']]
        chat=install/'chat/chat-keeper/keep.txt';chat.parent.mkdir(parents=True,exist_ok=True);chat.write_text('do not delete',encoding='utf-8')
        obsolete=install/'_internal/arise-obsolete.txt';obsolete.write_text('stale managed file')
        run_setup();new=ready(descriptor['pid']);new_remote=RemoteAssistant(new,data)
        for process in [old_daemon,*old_children,*old_ui]:
            if process.is_running():raise RuntimeError('Old owned process survived replacement: '+str(process.pid))
        if chat.read_text()!='do not delete' or obsolete.exists():raise RuntimeError('Installer data preservation/managed cleanup failed')
        notes=json.loads(new_remote.call_tool('memory.search',{'query':'Survives'})['content'][0]['text'])['notes']
        if not notes or new_remote.status()['version']!=__version__:raise RuntimeError('Version or persisted memory incorrect')
        if not (install/'bundle/python/python.exe').is_file():raise RuntimeError('Missing runtime for private tools')
        report={'fresh_install':'passed','replace_running_ui_daemon_pi':'passed','owned_children_closed':len(old_children),'user_chat_preserved':'passed','memory_preserved':'passed','stale_managed_file_removed':'passed','restarted_version':__version__}
    finally:stop()
Path('artifacts/installer-upgrade.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
