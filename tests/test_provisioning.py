import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from arise_app.bundle import configure_bundle
from arise_app.discovery import command_available, detect


class ProvisioningTests(unittest.TestCase):
    def bundle(self, root):
        bundle=root/'bundle';bundle.mkdir()
        (bundle/'pi.js').write_text('// fixture')
        gentle=bundle/'gentle';gentle.mkdir();(gentle/'extensions').mkdir()
        (gentle/'package.json').write_text(json.dumps({'name':'gentle-pi','version':'4.0.0'}))
        (bundle/'manifest.json').write_text(json.dumps({
            'pi_command':[sys.executable,'@bundle/pi.js'],'gentle_path':'@bundle/gentle',
            'mcp':{'screenview':{'command':[sys.executable,'@bundle/pi.js'],'enabled':True}}}))
        config={'onboarding_complete':True,'pi_command':[sys.executable,str(root/'deleted.js')],
                'gentle_path':str(root/'deleted'),'mcp':{'screenview':{'command':['missing-tool'],'enabled':False}}}
        runtime=SimpleNamespace(storage=SimpleNamespace(config=config),emit=lambda *args:None)
        runtime.settings=lambda changes:config.update(changes)
        return runtime

    def test_completed_onboarding_repairs_missing_engines_and_preserves_disabled_tools(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);runtime=self.bundle(root)
            with patch('arise_app.bundle.application_root',return_value=root):
                result=configure_bundle(runtime)
                again=configure_bundle(runtime)
            self.assertIn('pi_command',result['configured'])
            self.assertEqual(runtime.storage.config['gentle_path'],str(root/'bundle/gentle'))
            self.assertFalse(runtime.storage.config['mcp']['screenview']['enabled'])
            self.assertEqual(again['configured'],[])

    def test_valid_custom_pi_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);runtime=self.bundle(root)
            runtime.storage.config['pi_command']=[sys.executable]
            with patch('arise_app.bundle.application_root',return_value=root):
                configure_bundle(runtime)
            self.assertEqual(runtime.storage.config['pi_command'],[sys.executable])

    def test_missing_script_is_not_installed_just_because_host_exists(self):
        self.assertFalse(command_available([sys.executable,'does-not-exist-arise.js']))
        self.assertTrue(command_available([sys.executable]))

    def test_stale_gentle_setting_is_not_an_installed_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            (root/'settings.json').write_text(json.dumps({'packages':['npm:gentle-pi']}))
            result=detect({'pi_command':[sys.executable]},root)
            self.assertFalse(result['gentle_installed_package'])

    def test_incomplete_bundle_does_not_write_configuration(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);runtime=self.bundle(root)
            before=json.loads(json.dumps(runtime.storage.config))
            (root/'bundle/pi.js').unlink()
            with patch('arise_app.bundle.application_root',return_value=root):
                with self.assertRaisesRegex(RuntimeError,'incompleto'):configure_bundle(runtime)
            self.assertEqual(runtime.storage.config,before)
