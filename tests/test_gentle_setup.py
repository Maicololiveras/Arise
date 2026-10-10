import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from arise_app.gentle_setup import validate_result, wait_for_installer, prepare_installer_stage
from scripts.prepare_gentle_installer import adapt_bootstrap
from arise_app.bundle import configure_bundle
from arise_app.github_access import github_opener, gh_executable
import test_provisioning
from scripts.build_complete_zip import build

class GentleSetupTests(unittest.TestCase):
    def test_bootstrap_profile_staging_preserves_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            entry=Path(temp)/'bootstrap.cmd'
            original='set ROOT=%LOCALAPPDATA%\n$env:LOCALAPPDATA $env:LOCALAPPDATA $env:LOCALAPPDATA\ncheck acl-mask ancestor-reparse private-owner\n'
            entry.write_text(original)
            adapt_bootstrap(entry)
            self.assertEqual(entry.read_text(),original.replace('%LOCALAPPDATA%','%ARISE_GENTLE_STAGE%').replace('$env:LOCALAPPDATA','$env:ARISE_GENTLE_STAGE'))
            with self.assertRaises(RuntimeError):adapt_bootstrap(entry)

    def test_stage_failure_removes_only_new_empty_directory(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as temp:
            existing=Path(temp)/'keep';existing.mkdir();(existing/'data').write_text('keep')
            with patch.dict(os.environ,{'USERPROFILE':temp,'SystemRoot':temp}),patch('arise_app.gentle_setup.subprocess.CREATE_NO_WINDOW',0,create=True),patch('arise_app.gentle_setup.subprocess.run',return_value=SimpleNamespace(returncode=1)):
                with self.assertRaisesRegex(RuntimeError,'carpeta privada'):prepare_installer_stage()
            self.assertEqual(list(Path(temp).iterdir()),[existing])
            self.assertEqual((existing/'data').read_text(),'keep')

    def test_stage_passes_path_as_environment_data(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as temp:
            def run(command,**kwargs):
                stage=kwargs['env']['ARISE_GENTLE_STAGE']
                self.assertTrue(Path(stage).is_dir())
                self.assertNotIn(stage,str(command))
                self.assertEqual(kwargs['env']['LOCALAPPDATA'],'unchanged')
                return SimpleNamespace(returncode=0)
            with patch.dict(os.environ,{'USERPROFILE':temp,'SystemRoot':temp,'LOCALAPPDATA':'unchanged'}),patch('arise_app.gentle_setup.subprocess.CREATE_NO_WINDOW',0,create=True),patch('arise_app.gentle_setup.subprocess.run',side_effect=run):
                stage,env=prepare_installer_stage()
                self.assertEqual(stage.parent,Path(temp));stage.rmdir()

    def test_native_windows_stage_owner_and_parent_preservation(self):
        if os.name!='nt':return  # Native assertion executes in Windows CI only.
        powershell=str(Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe')
        def check(script,env=None):
            result=subprocess.run([powershell,'-NoProfile','-NonInteractive','-Command',script],env=env,capture_output=True,text=True,check=True)
            return result.stdout.strip()
        parents="foreach($p in @($env:USERPROFILE,$env:LOCALAPPDATA)){([IO.Directory]::GetAccessControl($p)).GetSecurityDescriptorSddlForm([Security.AccessControl.AccessControlSections]::All)}"
        before=check(parents)
        stage,env=prepare_installer_stage()
        try:
            check("$a=[IO.Directory]::GetAccessControl($env:ARISE_GENTLE_STAGE); $me=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value; if($a.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne $me -or -not $a.AreAccessRulesProtected){exit 1}; foreach($r in $a.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])){if(@($me,'S-1-5-18','S-1-5-32-544') -notcontains $r.IdentityReference.Value){exit 2}}",env)
            self.assertEqual(check(parents),before)
        finally:stage.rmdir()

    def test_failed_installer_reports_exit_and_acl_without_waiting_an_hour(self):
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);log=root/'bootstrap.log';log.write_text('private storage failed. Reason: acl-mask')
            process=Mock();process.poll.return_value=1
            with self.assertRaisesRegex(RuntimeError,'código 1.*acl-mask'):
                wait_for_installer(process,root/'result.json',log,3600)

    def test_success_result_is_accepted_while_wizard_remains_open(self):
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as temp:
            result=Path(temp)/'result.json';result.write_text('{}')
            process=Mock()
            wait_for_installer(process,result,Path(temp)/'log',3600)
            process.poll.assert_not_called()

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
                self.assertEqual(config['pi_command'],[sys.executable,str((pi/'dist/bundle/cli.js').resolve())])
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
