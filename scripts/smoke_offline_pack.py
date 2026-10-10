"""Exercise the actual Windows model pack in the shipped frozen daemon."""
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

package=Path('dist/ARISE').resolve()
archive=Path('dist/ARISE-Models-Windows.zip').resolve()
with tempfile.TemporaryDirectory(prefix='arise-offline-smoke-') as temporary:
    root=Path(temporary)
    env={**os.environ,'ARISE_SKIP_NETWORK_SETUP':'1','ARISE_CHAT_ROOT':str(root/'chats')}
    process=subprocess.Popen([str(package/'ARISE-host.exe'),'--engine',str(package/'ARISE.exe'),'--data-dir',str(root/'data')],env=env)
    remote=None
    try:
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            descriptor=read_descriptor(root/'data')
            if ping(descriptor):break
            if process.poll() is not None:raise RuntimeError('Frozen daemon exited')
            time.sleep(.2)
        else:raise TimeoutError('Frozen daemon readiness timeout')
        remote=RemoteAssistant(descriptor,root/'data')
        result=remote.request('models/offline/install',{'path':str(archive)},timeout=900)
        assert result['inference']=='passed',result
        config=remote.request('config')
        assert Path(config['local_stt_model']).is_file()
        assert remote.status()['model_service']['state']=='stopped'
        assert config['voice_task_engine']=='gentle'
        assert Path(config['piper_model']).is_file()
        report={'one_click_install':result,'frozen_daemon':'passed','local_inference':'passed','platform':'windows-x64'}
        Path('artifacts/offline-pack-validation.json').write_text(json.dumps(report,indent=2))
    finally:
        if remote:remote.shutdown()
        try:process.wait(timeout=30)
        except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=5)
