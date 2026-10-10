import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from arise_app.assistant import Assistant

class ProjectTests(unittest.TestCase):
    def test_git_worktrees_copy_dirty_files_and_keep_chats_isolated(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);repo=root/'project with spaces';repo.mkdir()
            def git(*args):return subprocess.run(['git','-C',str(repo),*args],check=True,capture_output=True)
            git('init');git('config','user.name','ARISE tests');git('config','user.email','test@example.invalid')
            (repo/'tracked.txt').write_text('committed');git('add','.');git('commit','-m','fixture')
            (repo/'tracked.txt').write_text('dirty current work');(repo/'new.txt').write_text('untracked')
            r=Assistant(root/'data')
            try:
                first=r.select_project(str(repo))['id']
                r.storage.message(first,'user','Chat original')
                r.storage.config['agent_model']='first-model'
                second=r.switch_conversation()['id'];session=r.sessions.get(second)
                self.assertEqual(session['kind'],'worktree')
                copy=Path(session['workspace'])
                self.assertEqual((copy/'tracked.txt').read_text(),'dirty current work')
                self.assertEqual((copy/'new.txt').read_text(),'untracked')
                r.call_tool('files.write',{'path':'tracked.txt','text':'Only second chat'})
                r.storage.config['agent_model']='second-model'
                self.assertEqual((repo/'tracked.txt').read_text(),'dirty current work')
                r.switch_conversation(first)
                self.assertEqual(Path(r.storage.config['workspace']),repo.resolve())
                self.assertEqual(r.storage.messages(first)[0]['text'],'Chat original')
                self.assertEqual(r.storage.config['agent_model'],'first-model')
                self.assertEqual(r.storage.messages(second),[])
                self.assertEqual(len(r.project_catalog()['chats']),2)
                checkpoint=json.loads(Path(session['folder'],'session.json').read_text())
                self.assertEqual(checkpoint['state'],'suspended')
                r.switch_conversation(second)
                self.assertEqual(r.storage.config['agent_model'],'second-model')
            finally:r.close();r.storage.db.close()

    def test_subdirectory_chat_copies_only_selected_folder(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);repo=root/'repo';repo.mkdir()
            subprocess.run(['git','-C',str(repo),'init'],check=True,capture_output=True)
            selected=repo/'selected';selected.mkdir()
            (selected/'inside.txt').write_text('inside')
            (repo/'outside.txt').write_text('outside')
            r=Assistant(root/'data')
            try:
                old=r.select_project(str(selected))['id']
                new=r.switch_conversation()['id']
                session=r.sessions.get(new)
                self.assertNotEqual(old,new)
                self.assertEqual(session['kind'],'copy')
                workspace=Path(session['workspace'])
                self.assertEqual((workspace/'inside.txt').read_text(),'inside')
                self.assertFalse((workspace/'outside.txt').exists())
                self.assertEqual(r.storage.messages(new),[])
            finally:r.close();r.storage.db.close()

    def test_plain_directory_copies_and_active_chat_survives_restart(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);source=root/'plain';source.mkdir();(source/'data.txt').write_text('same')
            r=Assistant(root/'data');r.select_project(str(source));identity=r.switch_conversation()['id']
            self.assertEqual(r.sessions.get(identity)['kind'],'copy')
            workspace=r.storage.config['workspace'];r.close();r.storage.db.close()
            r=Assistant(root/'data')
            try:
                self.assertEqual(r.conversation,identity)
                self.assertEqual(r.storage.config['workspace'],workspace)
                self.assertEqual(Path(workspace,'data.txt').read_text(),'same')
            finally:r.close();r.storage.db.close()

    def test_switch_aborts_hidden_process_and_checkpoints_chat(self):
        with tempfile.TemporaryDirectory() as temporary:
            r=Assistant(temporary)
            r.storage.config.update(pi_command=[sys.executable,str(Path(__file__).parent/'fake_agent.py'),'--pi'],mcp={})
            try:
                old=r.conversation;r.connect_pi();process=r.pi.process
                r.switch_conversation()
                self.assertIsNotNone(process.poll())
                self.assertIsNone(r.pi)
                self.assertTrue(Path(r.sessions.get(old)['folder'],'messages.json').is_file())
                r.switch_conversation(old);r.connect_pi();self.assertNotEqual(r.pi.process.pid,process.pid)
            finally:r.close();r.storage.db.close()
