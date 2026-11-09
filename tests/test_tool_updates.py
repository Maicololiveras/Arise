import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from arise_app.tool_setup import auto_setup, installed_record, tool_update_available


class ToolUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.runtime = SimpleNamespace(storage=SimpleNamespace(root=self.root, config={'mcp':{}}),
            transition_lock=threading.RLock(), busy=False, desktop=False, credentials=None, emit=Mock())
        self.os_patch = patch('arise_app.tool_setup.os', SimpleNamespace(name='nt'))
        self.os_patch.start(); self.addCleanup(self.os_patch.stop)

    def managed(self, name, record, enabled=True):
        folder=self.root/'tools'/('runtime-'+name)
        executable=folder/name/(name+'.exe');executable.parent.mkdir(parents=True)
        executable.write_bytes(b'fixture')
        (folder/'installed.json').write_text(json.dumps({name:record}))
        self.runtime.storage.config['mcp'][name]={'command':[str(executable)],'enabled':enabled}
        return folder

    def test_each_public_tool_updates_only_when_published_identity_changes(self):
        for name in ('screenview','inputcontrol','forge'):
            self.managed(name, {'tag':'old','sha256':'a'})
        with patch('arise_app.tool_setup.github_token', return_value=None), \
             patch('arise_app.public_tools.fetch_manifest', side_effect=lambda n:{'tag':'old' if n=='forge' else 'new','sha256':'a'}), \
             patch('arise_app.tool_setup.setup_desktop_tools') as install:
            auto_setup(self.runtime)
            self.assertEqual([c.args[1] for c in install.call_args_list],[['screenview'],['inputcontrol']])

    def test_hash_change_without_version_change_is_detected(self):
        self.managed('forge', {'tag':'same','sha256':'old'})
        with patch('arise_app.public_tools.fetch_manifest', return_value={'tag':'same','sha256':'new'}):
            self.assertTrue(tool_update_available(self.runtime,'forge'))

    def test_custom_commands_and_disabled_tools_are_not_replaced(self):
        self.managed('screenview',{},enabled=False)
        custom=self.root/'custom.exe';custom.write_bytes(b'fixture')
        for name in ('inputcontrol','forge'):
            self.runtime.storage.config['mcp'][name]={'command':[str(custom)]}
        with patch('arise_app.tool_setup.github_token', return_value=None), \
             patch('arise_app.public_tools.fetch_manifest') as fetch, \
             patch('arise_app.tool_setup.setup_desktop_tools') as install:
            auto_setup(self.runtime)
            fetch.assert_not_called();install.assert_not_called()

    def test_offline_component_does_not_block_other_updates(self):
        for name in ('screenview','inputcontrol','forge'):self.managed(name,{'tag':'old','sha256':'a'})
        def fetch(name):
            if name=='screenview':raise OSError('offline')
            return {'tag':'new','sha256':'b'}
        with patch('arise_app.tool_setup.github_token', return_value=None), \
             patch('arise_app.public_tools.fetch_manifest', side_effect=fetch), \
             patch('arise_app.tool_setup.setup_desktop_tools') as install:
            auto_setup(self.runtime)
            self.assertEqual([c.args[1] for c in install.call_args_list],[['inputcontrol'],['forge']])

    def test_private_transcription_compares_commit_with_existing_access(self):
        self.managed('transcripcion',{'commit':'old'})
        with patch('arise_app.tool_setup.github_token', return_value='fixture'), \
             patch('arise_app.tool_setup.github_opener'), \
             patch('arise_app.tool_setup.github_json', side_effect=[{'default_branch':'main'},{'sha':'new'}]):
            self.assertTrue(tool_update_available(self.runtime,'transcripcion'))
        with patch('arise_app.tool_setup.github_token', return_value=None), patch('arise_app.tool_setup.github_json') as fetch:
            self.assertFalse(tool_update_available(self.runtime,'transcripcion'));fetch.assert_not_called()

    def test_active_work_defers_check_and_active_runtime_owns_metadata(self):
        self.managed('forge',{'tag':'active','sha256':'a'})
        (self.root/'tools'/'installed.json').write_text(json.dumps({'forge':{'tag':'unrelated'}}))
        self.assertEqual(installed_record(self.runtime,'forge')['tag'],'active')
        for field in ('busy','desktop'):
            setattr(self.runtime,field,True)
            with patch('arise_app.tool_setup.setup_desktop_tools') as install:
                auto_setup(self.runtime);install.assert_not_called()
            setattr(self.runtime,field,False)

    def test_activation_records_new_version_and_next_start_does_not_download_again(self):
        self.managed('inputcontrol',{'tag':'old','sha256':'old'})
        rt=self.runtime
        for name in ('screenview','forge','transcripcion'):
            rt.storage.config['mcp'][name]={'enabled':False}
        rt.mcp={};rt.settings=lambda changes:rt.storage.config.update(changes)
        def connect(name):
            client=Mock(tools=[{'name':'status'}]);rt.mcp[name]=client;return client
        rt.connect_mcp=connect
        latest={'tag':'new','sha256':'new'}
        def download(name, directory, notify):
            exe=directory/name/'inputcontrol-mcp.exe';exe.parent.mkdir();exe.write_bytes(b'fixture')
            return {'command':[str(exe)],'enabled':True},latest
        with patch('arise_app.public_tools.fetch_manifest',return_value=latest), \
             patch('arise_app.public_tools.install_public_tool',side_effect=download) as install:
            auto_setup(rt);auto_setup(rt)
            self.assertEqual(install.call_count,1)
            self.assertEqual(installed_record(rt,'inputcontrol'),latest)

    def test_failed_update_keeps_previous_command_and_provenance(self):
        old={'tag':'old','sha256':'old'}
        self.managed('inputcontrol',old)
        rt=self.runtime;old_command=rt.storage.config['mcp']['inputcontrol']['command'][:]
        for name in ('screenview','forge','transcripcion'):
            rt.storage.config['mcp'][name]={'enabled':False}
        rt.mcp={};rt.settings=lambda changes:rt.storage.config.update(changes)
        bad=Mock(tools=[])
        def connect(name):rt.mcp[name]=bad;return bad
        rt.connect_mcp=connect
        latest={'tag':'new','sha256':'new'}
        with patch('arise_app.public_tools.fetch_manifest',return_value=latest), \
             patch('arise_app.public_tools.install_public_tool',return_value=({'command':['new.exe'],'enabled':True},latest)):
            auto_setup(rt)
        self.assertEqual(rt.storage.config['mcp']['inputcontrol']['command'],old_command)
        self.assertEqual(installed_record(rt,'inputcontrol'),old)
        bad.close.assert_called_once()
