import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from arise_app.gentle_setup import validate_result
from arise_app.bundle import configure_bundle
from arise_app.github_access import github_opener, gh_executable
import test_provisioning
from scripts.build_complete_zip import build

class GentleSetupTests(unittest.TestCase):
    def test_both_channels_adopt_the_cli_declared_by_gentle_pi(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);pi=root/'configured-pi';gentle=root/'gentle';home=root/'agent'
            for path in (pi/'dist/bundle',gentle/'extensions',home):path.mkdir(parents=True)
            (pi/'dist/bundle/cli.js').write_text('')
            (pi/'package.json').write_text(json.dumps({'name':'@earendil-works/pi-coding-agent','bin':{'pi':'dist/bundle/cli.js'}}))
            (gentle/'package.json').write_text(json.dumps({'name':'gentle-pi'}))
            for channel in ('main','release'):
                result={'status':'ready','channel':channel,'pi_root':str(pi),'gentle_root':str(gentle),'agent_home':str(home)}
                config=validate_result(result,sys.executable)
                self.assertEqual(config['pi_command'],[sys.executable,str(pi/'dist/bundle/cli.js')])
                self.assertEqual(config['gentle_agent_home'],str(home))
                self.assertEqual(config['gentle_channel'],channel)
            (pi/'dist/bundle/cli.js').unlink()
            with self.assertRaises(ValueError):validate_result(result,sys.executable)

    def test_missing_official_pi_is_never_replaced_by_bundle(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);runtime=test_provisioning.ProvisioningTests().bundle(root)
            runtime.storage.config['gentle_agent_home']=str(root/'official-home')
            original=runtime.storage.config['pi_command'][:]
            with patch('arise_app.bundle.application_root',return_value=root):configure_bundle(runtime)
            self.assertEqual(runtime.storage.config['pi_command'],original)
            self.assertEqual(runtime.storage.config['gentle_path'],str(root/'deleted'))

    def test_zip_runs_upgrading_installer_with_model_parameter(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'ARISE-Setup.exe').write_bytes(b'fixture');models=root/'models.zip';models.write_bytes(b'fixture')
            build(root/'ARISE',models,root/'complete.zip')
            with zipfile.ZipFile(root/'complete.zip') as archive:
                self.assertIn('ARISE-Setup.exe',archive.namelist())
                launcher=archive.read('Configurar ARISE.cmd').decode()
                self.assertIn('/ARISE-MODELS=',launcher)
                self.assertNotIn('ARISE\\ARISE.exe',launcher)

    def test_bundled_gh_download_uses_environment_not_secret_arguments(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);gh=root/'bundle/gh/gh.exe';gh.parent.mkdir(parents=True);gh.write_bytes(b'fixture')
            def run(command,**kwargs):
                self.assertEqual(command[0],str(gh))
                self.assertNotIn('fixture-secret',str(command))
                self.assertEqual(kwargs['env']['GH_TOKEN'],'fixture-secret')
                kwargs['stdout'].write(b'{"ok":true}')
                from types import SimpleNamespace
                return SimpleNamespace(returncode=0)
            with patch('arise_app.bundle.application_root',return_value=root),patch('arise_app.github_access.subprocess.run',side_effect=run):
                self.assertEqual(gh_executable(),str(gh))
                with github_opener('fixture-secret')('https://api.github.com/repos/owner/repo') as response:self.assertEqual(json.load(response),{'ok':True})
