import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from arise_app.antigravity import environment, validate, VERSION

class AntigravityTests(unittest.TestCase):
    def fixture(self, root):
        gentle=root/'node_modules/gentle-pi';gentle.mkdir(parents=True)
        bridge=gentle.parent/'@3d24rd0/pi-antigravity-bridge'
        (bridge/'src').mkdir(parents=True)
        (bridge/'src/entry.ts').write_text('fixture')
        (bridge/'package.json').write_text(json.dumps({'name':'@3d24rd0/pi-antigravity-bridge','version':VERSION}))
        return {'gentle_path':str(gentle),'antigravity_enabled':True},bridge

    def test_disabled_does_not_activate_from_parent(self):
        self.assertEqual(environment({'ARISE_AGY_ROOT':'foreign','HOME':'original'},{}),{'HOME':'original'})

    def test_missing_or_wrong_package_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            config,bridge=self.fixture(Path(tmp))
            self.assertEqual(validate(config),bridge.resolve())
            (bridge/'src/entry.ts').unlink()
            with self.assertRaises(ValueError):validate(config)
        with self.assertRaises(ValueError):validate({'antigravity_enabled':'true'})

    def test_permission_overrides_do_not_bypass_chat_consent(self):
        with tempfile.TemporaryDirectory() as tmp:
            config,_=self.fixture(Path(tmp))
            source={'AGY_APPROVALS':'off','AGY_SKIP_PERMISSIONS':'true','AGY_READONLY':'false','AGY_ASK_TOOL':'on'}
            env=environment(source,config)
            self.assertEqual(env['AGY_READONLY'],'true')
            self.assertEqual(env['AGY_APPROVALS'],'shadow')
            self.assertEqual(env['AGY_APPROVALS_MODE'],'ask')
            self.assertEqual(env['AGY_SKIP_PERMISSIONS'],'false')
            self.assertEqual(env['AGY_ASK_TOOL'],'off')
            config['code_enabled']=True
            self.assertEqual(environment(source,config)['AGY_READONLY'],'false')
            self.assertEqual(source['AGY_APPROVALS'],'off')

    def test_real_upstream_extension_rpc_adapter(self):
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            env={**os.environ,'HOME':tmp,'USERPROFILE':tmp,'ARISE_AGY_ROOT':str(root/'vendor/node_modules/@3d24rd0/pi-antigravity-bridge'),'AGY_ASK_TOOL':'off','AGY_WEB_TOOLS':'off'}
            result=subprocess.run(['node',str(root/'tests/antigravity.mjs')],env=env,capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
