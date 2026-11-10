import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from arise_app import memory_selection as m

class MemorySelectionTests(unittest.TestCase):
    def test_private_is_unchanged(self):
        env = {'ENGRAM_BIN': '/custom', 'HOME': '/home'}
        self.assertEqual(m.selection(env, {}), env)

    def test_shared_preserves_saved_private_binary_but_does_not_inject_it(self):
        env = {'PATH': '/bin'}
        result = m.selection(env, {'memory_mode': 'shared', 'engram_bin': '/saved'})
        self.assertNotIn('ENGRAM_BIN', result)
        self.assertEqual(result['ARISE_MEMORY_MODE'], 'shared')

    def test_inherited_conflicts_are_rejected(self):
        for key in m.CONFLICTS:
            with self.subTest(key=key), self.assertRaises(ValueError):
                m.selection({key: 'explicit'}, {'memory_mode':'shared'})

    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):
            m.selection({}, {'memory_mode':'other'})

    def test_final_owned_environment_remains_isolated_without_private_memory(self):
        from arise_app.owned_engine import environment
        from arise_app.engram_setup import engine_environment
        with tempfile.TemporaryDirectory() as root:
            config = dict(memory_mode='shared', engine_mode='bundled', owned_engine_root=root,
                gentle_agent_home=root+'/agent', gentle_path=root+'/gentle',
                pi_command=['/node','/pi'], engram_bin='/saved')
            env = environment(engine_environment({'HOME':root}, config), config)
            self.assertEqual(env['HOME'], str(Path(root)/'home'))
            for key in m.CONFLICTS: self.assertNotIn(key, env)
            self.assertEqual(env['ARISE_MEMORY_MODE'],'shared')

    def test_failed_probe_does_not_change_config(self):
        config={'memory_mode':'shared','pi_command':['node','pi'],'gentle_path':'/package'}
        original=config.copy()
        with patch('subprocess.run', side_effect=OSError), self.assertRaises(RuntimeError):
            m.validate(config, {})
        self.assertEqual(config,original)

class MemoryRuntimeTests(unittest.TestCase):
    def setUp(self):
        from arise_app.assistant import Assistant
        self.temp=tempfile.TemporaryDirectory()
        self.r=Assistant(self.temp.name)

    def tearDown(self):
        self.r.close();self.r.storage.db.close();self.temp.cleanup()

    def test_rejected_setting_preserves_connection_and_configuration(self):
        config=self.r.storage.config.copy()
        with patch('arise_app.memory_selection.validate',side_effect=RuntimeError('unavailable')), patch.object(self.r,'disconnect_pi') as disconnect:
            with self.assertRaises(RuntimeError):self.r.settings({'memory_mode':'shared'})
            disconnect.assert_not_called()
        self.assertEqual(config,self.r.storage.config)

    def test_successful_change_disconnects_and_persists(self):
        with patch('arise_app.memory_selection.validate'),patch.object(self.r,'disconnect_pi') as disconnect:
            self.r.settings({'memory_mode':'shared'})
            disconnect.assert_called_once()
        self.assertEqual(self.r.storage.config['memory_mode'],'shared')

    def test_rejected_delegate_leaves_no_task_files(self):
        r=self.r
        r.storage.config.update(code_enabled=True,gentle_agent_home=self.temp.name,pi_command=['node','pi'],memory_mode='shared')
        with patch('arise_app.terminal_tasks.sys.platform','win32'),patch.object(r,'ask_approval'),patch('arise_app.memory_selection.validate',side_effect=RuntimeError('unavailable')):
            with self.assertRaises(RuntimeError):r.terminals.delegate('Synthetic task')
        self.assertFalse(r.terminals.folder(r.conversation).exists())

    def test_status_requires_tool_evidence_and_error_is_sticky(self):
        r=self.r;r.storage.config['memory_mode']='shared'
        r.pi_event({'type':'arise_memory_status','state':'verifying'})
        self.assertEqual(r.memory_state,'verifying')
        with patch.object(r,'publish_activity'):
            r.pi_event({'type':'tool_execution_end','toolName':'mem_search','isError':False})
        self.assertEqual(r.memory_state,'connected')
        r.pi_event({'type':'arise_memory_status','state':'error'})
        with patch.object(r,'publish_activity'):
            r.pi_event({'type':'tool_execution_end','toolName':'mem_search','isError':False})
        self.assertEqual(r.memory_state,'error')
        r.disconnect_pi();self.assertEqual(r.memory_state,'configured')

    def test_actual_adapter_and_native_compatibility_contract(self):
        import subprocess
        root=Path(__file__).resolve().parents[1]
        package=root/'vendor/node_modules/gentle-pi'
        self.assertTrue((package/'runtime/gentle-shell-bundled.mjs').is_file())
        result=subprocess.run(['node',str(root/'tests/shared-memory.mjs'),str(package)],
                              cwd=root,text=True,capture_output=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)

class MemoryUiTests(unittest.TestCase):
    def test_selector_translates_without_changing_protocol_value(self):
        from PySide6.QtWidgets import QApplication
        from unittest.mock import Mock
        from arise_app.assistant import Assistant
        from arise_app.desktop import Settings
        from arise_app.i18n import LiveTranslator
        app=QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as root:
            runtime=Assistant(root);window=Settings(Mock(runtime=runtime))
            translator=LiveTranslator(app,'en')
            try:
                translator.refresh()
                combo=window.fields['memory_mode']
                self.assertEqual(combo.currentText(),'ARISE private memory')
                combo.setCurrentIndex(1);translator.refresh()
                self.assertEqual(combo.currentText(),'Shared local Engram server')
                self.assertEqual(window.changes()['memory_mode'],'shared')
                translator.set_language('es')
                self.assertEqual(combo.currentText(),'Servidor local compartido de Engram')
            finally:
                translator.close();window.close();runtime.close();runtime.storage.db.close()
