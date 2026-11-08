"""Exercise the shipped Rust host, frozen daemon, Pi/Gentle and Qt renderer."""
import json
import os
import subprocess
import sys
import tempfile
import time
import psutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from arise_app.daemon import read_descriptor,ping
from arise_app.remote import RemoteAssistant

package=Path(sys.argv[1]).resolve()
report={}
with tempfile.TemporaryDirectory(prefix='arise-frozen-') as temporary:
    root=Path(temporary)
    agent=root/'data/engine/agent';agent.mkdir(parents=True)
    (agent/'settings.json').write_text(json.dumps({'packages':[],'telemetry':False}),encoding='utf-8')
    (agent/'models.json').write_text(json.dumps({'providers':{'arise-smoke':{'baseUrl':'http://127.0.0.1:1/v1','api':'openai-completions','apiKey':'fixture-only','models':[{'id':'fixture','input':['text'],'contextWindow':32000,'maxTokens':1000}]}}}),encoding='utf-8')
    # Upgrade/portable relocation: completed onboarding must not pin deleted paths.
    data=root/'data'
    (data/'settings.json').write_text(json.dumps({'onboarding_complete':True,
        'pi_command':[str(package/'bundle/node/node.exe'),str(root/'deleted/cli.js')],
        'gentle_path':str(root/'deleted/gentle')}),encoding='utf-8')
    # This checks shipped dependencies; public tool acquisition has its own
    # tests and must not race the isolated fixture or depend on network timing.
    env={**os.environ,'PI_CODING_AGENT_DIR':str(root/'invalid-global-agent'),'GENTLE_PI_GENTLE_AI_DEV_BINARY':'invalid-global-dev-binary','PATH':str(Path(os.environ['SystemRoot'])/'System32'),'PI_OFFLINE':'1','ARISE_SKIP_NETWORK_SETUP':'1','QT_QPA_PLATFORM':'offscreen','ARISE_CHAT_ROOT':str(root/'chats')}
    engine=package/'ARISE.exe';host=package/'ARISE-host.exe'
    process=subprocess.Popen([str(host),'--engine',str(engine),'--data-dir',str(root/'data')],env=env)
    remote=None
    try:
        deadline=time.monotonic()+40
        while time.monotonic()<deadline:
            descriptor=read_descriptor(root/'data')
            if ping(descriptor):break
            if process.poll() is not None:raise RuntimeError('The shipped host/engine exited: '+str(process.returncode))
            time.sleep(.1)
        else:raise TimeoutError('The shipped daemon did not start')
        remote=RemoteAssistant(descriptor,root/'data')
        remote.settings({'agent_provider':'arise-smoke','agent_model':'fixture','thinking':'off','pi_extra_args':['--offline','--no-skills','--no-context-files']})
        state=remote.connect_pi()
        if not state.get('gentleVerified'):raise RuntimeError('Bundled Gentle Shell did not load')
        settings=json.loads((data/'settings.json').read_text(encoding='utf-8-sig'))
        if settings['gentle_agent_home'] != str(agent): raise RuntimeError('Engine adopted a foreign home')
        if settings['engram_bin'] != str(package/'bundle/engram/engram.exe'): raise RuntimeError('Engine adopted a foreign Engram')
        if 'mem_search' not in remote.status()['capabilities']['pi_tools_observed']:
            raise RuntimeError('Owned memory tools were not registered')
        owned_memory=[p for p in psutil.Process(process.pid).children(recursive=True) if p.name().lower() == 'engram.exe']
        if not owned_memory or not (data/'engine/memory').is_dir():
            raise RuntimeError('Bundled Engram did not start in its private store')
        report['owned_engine_without_global_path']='passed'
        report['owned_engram']='passed'
        # Adopt a configured Gentle home and its package metadata Pi entry.
        # The home already declares Gentle: loading it twice must be avoided.
        gentle=package/'bundle/node/node_modules/gentle-pi'
        pi=package/'bundle/node/node_modules/@earendil-works/pi-coding-agent'
        cli=json.loads((pi/'package.json').read_text(encoding='utf-8'))['bin']['pi']
        (agent/'settings.json').write_text(json.dumps({'packages':[str(gentle)],'telemetry':False}),encoding='utf-8')
        remote.settings({'engine_mode':'external','gentle_path':str(gentle),'gentle_agent_home':str(agent),
            'pi_command':[str(package/'bundle/node/node.exe'),str(pi/cli)],
            'pi_extra_args':['--offline','--no-skills','--no-context-files']})
        if not remote.connect_pi().get('gentleVerified'):raise RuntimeError('Configured Gentle home/Pi did not connect')
        if any(p.is_running() for p in owned_memory): raise RuntimeError('Owned Engram survived engine replacement')
        report['configured_gentle_pi']='passed'
        remote.call_tool('memory.save' ,{'text':'Frozen application smoke test'})
        report.update(host='passed',frozen_daemon='passed',bundled_pi_gentle='passed',stale_dependencies_repaired='passed',memory='passed')
    finally:
        if remote:remote.shutdown()
        try:process.wait(timeout=15)
        except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=5)
    env['PATH']=os.environ.get('PATH','')  # Remaining renderer/voice checks retain their original environment.
    output=Path('artifacts/frozen-orb.png').resolve();output.parent.mkdir(exist_ok=True)
    env['ARISE_CHAT_ROOT']=str(root/'renderer-chats')
    result=subprocess.run([str(engine),'--data-dir',str(root/'renderer'),'--screenshot',str(output)],env=env,timeout=30)
    if result.returncode or not output.is_file() or output.stat().st_size<1000:raise RuntimeError('The frozen Qt renderer did not produce its orb')
    report['frozen_qt_renderer']='passed'
    output=Path('artifacts/frozen-voice.json').resolve()
    result=subprocess.run([str(engine),'--voice-smoke',str(output)],env=env,timeout=60)
    if result.returncode or not output.is_file(): raise RuntimeError('The shipped offline voice engines/model failed')
    report['frozen_voice_engines']=json.loads(output.read_text(encoding='utf-8'))
Path('artifacts/frozen-application.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
