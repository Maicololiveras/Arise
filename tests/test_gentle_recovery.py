import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, Mock
from arise_app.discovery import detect, detect_gentle_installation

class RecoveryTests(unittest.TestCase):
    def test_recovered_installation_replaces_stale_global_paths(self):
        recovered = dict(pi_command=['node','owned/cli.js'],gentle_path='owned/gentle',gentle_agent_home='owned/home',gentle_channel='main')
        with patch('arise_app.discovery.detect_gentle_installation',return_value=recovered):
            found=detect(dict(pi_command=['old'],gentle_path='old',gentle_agent_home=''))
        self.assertEqual(found['pi_command'],recovered['pi_command'])
        self.assertEqual(found['gentle_agent_home'],'owned/home')

    def test_existing_explicit_home_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as tmp, patch('arise_app.discovery.detect_gentle_installation') as probe:
            detect(dict(pi_command=['missing-pi'],gentle_agent_home=tmp))
            probe.assert_not_called()

    def test_failed_probe_does_not_adopt_partial_installation(self):
        responses=[SimpleNamespace(returncode=0,stdout=json.dumps([{'dependencies':{'gentle-pi':{'path':'fixture'}}}])),SimpleNamespace(returncode=1,stdout='')]
        with patch('arise_app.discovery.shutil.which',side_effect=lambda x, **kwargs:x),patch('arise_app.discovery.gentle_valid',return_value=True),patch('arise_app.discovery.subprocess.run',side_effect=responses):
            self.assertIsNone(detect_gentle_installation())

    def test_linked_launcher_keeps_user_agent_home(self):
        from arise_app.discovery import linked_gentle_candidate
        with tempfile.TemporaryDirectory() as tmp:
            wrapper=Path(tmp)/'gentle-shell.cmd'
            wrapper.write_text('@echo off\nnode "%USERPROFILE%\\.pi\\agent\\npm\\node_modules\\gentle-pi\\bin\\gentle-shell.mjs" --link %*\n')
            env={'USERPROFILE':tmp,'PATH':tmp}
            with patch('arise_app.discovery.shutil.which',return_value=str(wrapper)):
                self.assertEqual(linked_gentle_candidate(env),Path(tmp)/'.pi/agent/npm/node_modules/gentle-pi')
            wrapper.write_text('node unknown.mjs %*')
            with patch('arise_app.discovery.shutil.which',return_value=str(wrapper)):
                self.assertIsNone(linked_gentle_candidate(env))

    def test_linked_installation_is_probed_before_pnpm(self):
        with patch('arise_app.discovery.linked_gentle_candidate',return_value=Path('/linked')), patch('arise_app.discovery.gentle_valid',return_value=True), patch('arise_app.discovery.resolve_pi',return_value=None), patch('arise_app.discovery.shutil.which',return_value='node'), patch('arise_app.discovery.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout='{}')) as run, patch('arise_app.gentle_setup.validate_result',return_value={'gentle_agent_home':'linked-home'}):
            self.assertEqual(detect_gentle_installation()['gentle_agent_home'],'linked-home')
            self.assertEqual(run.call_count,1)
            self.assertIn('--link',run.call_args.args[0])

    def test_failed_rpc_adoption_disconnects_and_restores_settings(self):
        import threading
        from arise_app.gentle_setup import adopt_gentle
        runtime=Mock();runtime.transition_lock=threading.RLock();runtime.busy=False
        runtime.storage.config={'gentle_path':'previous'}
        runtime.connect_pi.return_value={'gentleVerified':False}
        with self.assertRaises(RuntimeError):adopt_gentle(runtime,{'gentle_path':'candidate'})
        self.assertEqual(runtime.disconnect.call_count,2)
        self.assertEqual(runtime.settings.call_args.args[0],{'gentle_path':'previous'})
