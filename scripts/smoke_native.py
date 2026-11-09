"""Native frozen engine, private memory and offscreen renderer acceptance gate."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from arise_app.platforms import target
from arise_app.daemon import read_descriptor, ping
from arise_app.remote import RemoteAssistant

package = Path(sys.argv[1]).resolve()
identity = sys.argv[2]
if target() != identity: raise RuntimeError('Smoke runner architecture mismatch')
suffix = '.exe' if os.name == 'nt' else ''
engine = package / ('ARISE' + suffix)
report = {'target': identity, 'physical_audio_tested': False, 'desktop_control_tested': False}
with tempfile.TemporaryDirectory(prefix='arise-native-') as temporary:
    root = Path(temporary); data = root / 'data'; agent = data / 'engine/agent'; agent.mkdir(parents=True)
    (agent / 'settings.json').write_text(json.dumps({'packages': [], 'telemetry': False}))
    (agent / 'models.json').write_text(json.dumps({'providers': {'arise-smoke': {'baseUrl': 'http://127.0.0.1:1/v1', 'api': 'openai-completions', 'apiKey': 'fixture-only', 'models': [{'id': 'fixture', 'input': ['text'], 'contextWindow': 32000, 'maxTokens': 1000}]}}}))
    env = {**os.environ, 'PI_OFFLINE': '1', 'ARISE_SKIP_NETWORK_SETUP': '1', 'QT_QPA_PLATFORM': 'offscreen', 'ARISE_CHAT_ROOT': str(root / 'chats')}
    process = subprocess.Popen([str(package / ('ARISE-host' + suffix)), '--engine', str(engine), '--data-dir', str(data)], env=env)
    remote = None
    try:
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            descriptor = read_descriptor(data)
            if ping(descriptor): break
            if process.poll() is not None: raise RuntimeError('Frozen engine exited before readiness')
            time.sleep(.2)
        else: raise TimeoutError('Frozen daemon readiness timeout')
        remote = RemoteAssistant(descriptor, data)
        remote.settings({'agent_provider': 'arise-smoke', 'agent_model': 'fixture', 'thinking': 'off', 'pi_extra_args': ['--offline', '--no-skills', '--no-context-files']})
        if not remote.connect_pi().get('gentleVerified'): raise RuntimeError('Bundled Gentle did not load')
        if 'mem_search' not in remote.status()['capabilities']['pi_tools_observed']: raise RuntimeError('Memory tools missing')
        config = json.loads((data / 'settings.json').read_text())
        if Path(config['gentle_agent_home']).resolve() != agent.resolve(): raise RuntimeError('Foreign agent home')
        if Path(config['engram_bin']).resolve() != package / ('bundle/engram/engram' + suffix): raise RuntimeError('Foreign Engram')
        report.update(frozen_daemon='passed', bundled_engine='passed', memory_registration='passed')
    finally:
        if remote: remote.shutdown()
        try: process.wait(timeout=20)
        except subprocess.TimeoutExpired: process.terminate(); process.wait(timeout=10)
    output = Path('artifacts') / (identity + '-orb.png'); output.parent.mkdir(exist_ok=True)
    subprocess.run([str(engine), '--data-dir', str(root / 'renderer'), '--screenshot', str(output.resolve())], env=env, check=True, timeout=45)
    if not output.is_file() or output.stat().st_size < 1000: raise RuntimeError('Frozen renderer image missing')
    report['frozen_renderer'] = 'passed'
Path('artifacts', identity + '-smoke.json').write_text(json.dumps(report, indent=2))
