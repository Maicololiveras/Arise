import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

class LiveMemoryTests(unittest.TestCase):
    def setUp(self):
        from arise_app.assistant import Assistant
        self.temp=tempfile.TemporaryDirectory();self.r=Assistant(self.temp.name)
    def tearDown(self):
        self.r.pi=None;self.r.close();self.r.storage.db.close();self.temp.cleanup()
    def test_apply_reconnects_without_changing_chat_or_unrelated_settings(self):
        chat=self.r.conversation;before=self.r.storage.config.copy()
        with patch('arise_app.memory_selection.validate'), patch.object(self.r,'disconnect_pi') as disconnect, patch.object(self.r,'connect_pi') as connect:
            self.r.connect_memory({'memory_mode':'shared'})
            disconnect.assert_called_once();connect.assert_called_once()
        self.assertEqual(self.r.conversation,chat)
        self.assertEqual(self.r.memory_state,'verifying')
        self.assertEqual(self.r.storage.config,{**before,'memory_mode':'shared'})
    def test_failure_before_apply_preserves_live_connection(self):
        before=self.r.storage.config.copy()
        with patch('arise_app.memory_selection.validate',side_effect=RuntimeError('offline')),patch.object(self.r,'disconnect_pi') as disconnect,patch.object(self.r,'connect_pi') as connect:
            with self.assertRaisesRegex(RuntimeError,'offline'):self.r.connect_memory({'memory_mode':'shared'})
            disconnect.assert_not_called();connect.assert_not_called()
        self.assertEqual(before,self.r.storage.config)
    def test_connect_failure_is_visible_and_retry_supported(self):
        with patch('arise_app.memory_selection.validate'),patch.object(self.r,'connect_pi',side_effect=RuntimeError('startup')):
            with self.assertRaisesRegex(RuntimeError,'startup'):self.r.connect_memory({'memory_mode':'shared'})
        self.assertEqual(self.r.memory_state,'error')
        with patch('arise_app.memory_selection.validate'),patch.object(self.r,'connect_pi') as connect:
            self.r.connect_memory({'memory_mode':'private'});connect.assert_called_once()
        self.assertEqual(self.r.storage.config['memory_mode'],'private')
    def test_busy_and_unrelated_settings_rejected(self):
        with self.assertRaises(ValueError):self.r.connect_memory({'code_enabled':True})
        self.r.busy=True
        try:
            with self.assertRaises(RuntimeError):self.r.connect_memory({'memory_mode':'shared'})
        finally:self.r.busy=False
    def test_remote_endpoint_uses_long_timeout_and_refreshes_configuration(self):
        from arise_app.remote import RemoteAssistant
        r=object.__new__(RemoteAssistant);r.storage=Mock();r.request=Mock(side_effect=[{'memory':{}},{'memory_mode':'shared'}])
        r.connect_memory({'memory_mode':'shared'})
        self.assertEqual(r.request.call_args_list[0].args,('memory/connect',{'memory_mode':'shared'}))
        self.assertEqual(r.request.call_args_list[0].kwargs,{'timeout':120})
        self.assertEqual(r.storage.config,{'memory_mode':'shared'})
    def test_button_only_applies_memory_and_keeps_dialog_open(self):
        from PySide6.QtWidgets import QApplication
        from arise_app.desktop import Settings
        app=QApplication.instance() or QApplication([])
        controller=Mock(runtime=self.r);window=Settings(controller)
        try:
            window.show();window.fields['memory_mode'].setCurrentIndex(1)
            with patch.object(self.r,'connect_memory',return_value={}) as connect:
                window.connect_memory()
                operation,done,failed=controller.background.call_args.args
                self.assertFalse(window.memory_connect.isEnabled())
                done(operation());connect.assert_called_once_with({'memory_mode':'shared','engram_bin':''})
                self.assertTrue(window.isVisible());self.assertTrue(window.memory_connect.isEnabled())
        finally:window.close()

class RegistryBackportTests(unittest.TestCase):
    def test_actual_registry_preserves_files_and_supports_non_git_workspaces(self):
        root=Path(__file__).resolve().parents[1]
        result=subprocess.run(['node',str(root/'tests/skill-registry-backport.mjs'),str(root/'vendor/node_modules/gentle-pi')],capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)

class GitRuntimeTests(unittest.TestCase):
    def test_installed_git_is_added_only_to_child_path(self):
        from arise_app.git_runtime import with_git
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'Git/cmd';folder.mkdir(parents=True);(folder/'git.exe').touch()
            source={'PATH':'existing'};host={'ProgramFiles':tmp}
            with patch('arise_app.git_runtime.sys.platform','win32'),patch('arise_app.git_runtime.shutil.which',return_value=None):
                result=with_git(source,host)
            self.assertEqual(source,{'PATH':'existing'})
            self.assertEqual(result['PATH'],str(folder)+os.pathsep+'existing')
    def test_existing_git_is_preferred(self):
        from arise_app.git_runtime import with_git
        env={'PATH':'existing'}
        with patch('arise_app.git_runtime.sys.platform','win32'),patch('arise_app.git_runtime.shutil.which',return_value='git'):
            self.assertEqual(with_git(env,{}),env)
