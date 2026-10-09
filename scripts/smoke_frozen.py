"""Exercise the shipped Rust host, frozen daemon, Pi/Gentle and Qt renderer."""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from arise_app.daemon import read_descriptor,ping
from arise_app.remote import RemoteAssistant

package=Path(sys.argv[1]).resolve()
report={}
with tempfile.TemporaryDirectory(prefix='arise-frozen-') as temporary:
    root=Path(temporary)
    agent=root/'agent';agent.mkdir()
    (agent/'settings.json').write_text(json.dumps({'packages':[],'telemetry':False}),encoding='utf-8')
    (agent/'models.json').write_text(json.dumps({'providers':{'arise-smoke':{'baseUrl':'http://127.0.0.1:1/v1','api':'openai-completions','apiKey':'fixture-only','models':[{'id':'fixture','input':['text'],'contextWindow':32000,'maxTokens':1000}]}}}),encoding='utf-8')
    env={**os.environ,'PI_CODING_AGENT_DIR':str(agent),'PI_OFFLINE':'1','QT_QPA_PLATFORM':'offscreen'}
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
        remote.settings({'agent_provider':'arise-smoke','agent_model':'fixture','thinking':'off','pi_extra_args':['--offline','--no-extensions','--no-skills','--no-context-files']})
        state=remote.connect_pi()
        if not state.get('gentleVerified'):raise RuntimeError('Bundled Gentle Shell did not load')
        remote.call_tool('memory.save',{'text':'Frozen application smoke test'})
        report.update(host='passed',frozen_daemon='passed',bundled_pi_gentle='passed',memory='passed')
    finally:
        if remote:remote.shutdown()
        try:process.wait(timeout=15)
        except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=5)
    output=Path('artifacts/frozen-orb.png').resolve();output.parent.mkdir(exist_ok=True)
    result=subprocess.run([str(engine),'--data-dir',str(root/'renderer'),'--screenshot',str(output)],env=env,timeout=30)
    if result.returncode or not output.is_file() or output.stat().st_size<1000:raise RuntimeError('The frozen Qt renderer did not produce its orb')
    report['frozen_qt_renderer']='passed'
Path('artifacts/frozen-application.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
