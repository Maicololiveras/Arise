import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import threading
import unittest
from unittest.mock import Mock, patch
from arise_app import gentle_native_setup as n


class NativeSetupTests(unittest.TestCase):
    def test_reject_old_development_or_unidentified_executable(self):
        for output in ('gentle-ai 4.2.0', 'gentle-ai 4.3.1-dev', '4.3.1', 'unrelated 4.5.0'):
            with self.subTest(output=output), patch.object(n.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=output)):
                with self.assertRaises(RuntimeError):n.native_version(Path('gentle-ai.exe'),{})
        with patch.object(n.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='gentle-ai version 4.3.1')):
            self.assertEqual(n.native_version(Path('gentle-ai.exe'),{}),'4.3.1')

    def make_target(self, root):
        for name in ('manifest.json','selection.json','supervisor.exe','bin/gentle-shell.cmd','prefix/node_modules/gentle-pi/package.json'):
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('{}')
        (root/'manifest.json').write_text(json.dumps({'SupervisorSHA':hashlib.sha256((root/'supervisor.exe').read_bytes()).hexdigest()}))

    def test_owned_supervisor_only_and_no_rpc_adoption(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.make_target(root)
            with patch.object(n.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='gentle-shell 4.5.0')) as run:
                result=n.inspect_native_target(root,{})
            self.assertEqual(run.call_args.args[0],[str(root/'supervisor.exe'),'shell','launch',str(root),'gentle-shell','--version'])
            self.assertFalse(result['connected']);self.assertTrue(result['launcher_verified'])
            self.assertNotIn('pi_command',result)

    def test_incomplete_tampered_and_refused_install_never_adopted(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with patch.object(n.subprocess,'run') as run:
                with self.assertRaises(RuntimeError):n.inspect_native_target(root,{})
                self.make_target(root);(root/'supervisor.exe').write_text('changed')
                with self.assertRaisesRegex(RuntimeError,'manifiesto'):n.inspect_native_target(root,{})
                run.assert_not_called()
            self.make_target(root)
            with patch.object(n.subprocess,'run',return_value=SimpleNamespace(returncode=1,stdout='')):
                with self.assertRaisesRegex(RuntimeError,'rechazó'):n.inspect_native_target(root,{})

    def test_explicit_executable_must_be_absolute_and_real(self):
        for path in ('gentle-ai.exe','/missing/gentle-ai.exe','/tmp/launcher.cmd'):
            with self.assertRaises(ValueError):n.resolve_binary(Mock(),{},path)

    def test_console_keeps_existing_engine_and_does_not_auto_confirm(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);exe=root/'Gentle AI & test.exe';exe.write_text('test')
            runtime=Mock(busy=False,transition_lock=threading.RLock())
            runtime.storage.root=root
            process=Mock(returncode=0);process.poll.return_value=0
            with patch.object(n,'os',SimpleNamespace(name='nt',environ={'LOCALAPPDATA':folder,'ARISE_TOKEN':'secret'})),patch.object(n,'resolve_binary',return_value=exe),patch.object(n,'native_version',return_value='4.3.1'),patch.object(n,'inspect_native_target',return_value={'installed':True,'connected':False}),patch.object(n.subprocess,'CREATE_NEW_CONSOLE',16,create=True),patch.object(n.subprocess,'Popen',return_value=process) as launch:
                n.install_native_tui(runtime)
            self.assertEqual(launch.call_args.args[0],[str(exe)])
            self.assertEqual(launch.call_args.kwargs['creationflags'],16)
            self.assertNotIn('ARISE_TOKEN',launch.call_args.kwargs['env'])
            self.assertNotIn('shell',launch.call_args.kwargs)
            runtime.disconnect.assert_not_called();runtime.settings.assert_not_called();runtime.connect_pi.assert_not_called()
