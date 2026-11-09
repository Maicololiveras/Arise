import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from arise_app.assistant import Assistant
from arise_app.study import StudySession

class StudyTests(unittest.TestCase):
    def runtime(self):
        r=SimpleNamespace(conversation='a',chat_generation=0,busy=False,desktop_halted=False,transition_lock=threading.RLock(),tasks={},emit=Mock(),mcp={'screenview':object()},call_tool=Mock(return_value={'content':[{'type':'image','mimeType':'image/jpeg','data':'fixture'}]}),prompt=Mock(return_value={'task_id':'one'}))
        r.study=StudySession(r)
        return r
    def test_explicit_consent_and_bounded_interval(self):
        r=self.runtime()
        for options in ({},{'consent':True,'interval':0},{'consent':True,'interval':True}):
            with self.assertRaises(ValueError):r.study.control('start',**options)
        r.call_tool.assert_not_called()
    def test_stop_during_capture_prevents_submission_and_chat_switch_invalidates(self):
        r=self.runtime();s=r.study
        with patch.object(threading.Thread,'start'):
            s.control('start',consent=True)
        epoch=s.generation
        r.call_tool.side_effect=lambda *a:(s.stop_scheduling() or {'content':[{'type':'image'}]})
        s.observe(epoch);r.prompt.assert_not_called()
        self.assertFalse(s.active)
        with patch.object(threading.Thread,'start'):s.control('start',consent=True)
        r.chat_generation+=1
        self.assertFalse(s.valid(s.generation))
    def test_pause_does_not_cancel_unrelated_task_and_resume_is_explicit(self):
        r=self.runtime();r.stop=Mock();s=r.study
        with patch.object(threading.Thread,'start'):
            s.control('start',consent=True);s.control('pause');r.stop.assert_not_called()
            self.assertTrue(s.paused);s.control('resume');self.assertFalse(s.paused)
        s.close()
    def test_study_turn_rejects_side_effect_tools_even_if_code_authorized(self):
        with tempfile.TemporaryDirectory() as directory:
            r=Assistant(directory)
            try:
                r.study.guarded=True;r.storage.config['code_enabled']=True
                for tool,args in [('files.write',{'path':'bad.txt','text':'bad'}),('terminal.delegate',{'task':'run'}),('inputcontrol.click',{})]:
                    with self.assertRaises(RuntimeError):r.call_tool(tool,args)
                self.assertTrue(r.status()['study_read_only'])
            finally:r.close();r.storage.db.close()
    def test_capture_submits_image_and_guards_tool_calls(self):
        r=self.runtime();s=r.study
        with patch.object(threading.Thread,'start'):s.control('start',consent=True,context='material')
        s.observe(s.generation)
        self.assertTrue(s.guarded);self.assertEqual(s.task_id,'one')
        self.assertEqual(r.prompt.call_args.args[1][0]['type'],'image')
        s.close()
    def test_pause_running_turn_can_resume_without_replaying_cancelled_result(self):
        r=self.runtime();s=r.study
        def stop():
            s.stop_scheduling();r.busy=False;r.tasks['one']={'status':'error','error':'cancelled'}
        r.stop=stop
        with patch.object(threading.Thread,'start'):
            s.control('start',consent=True);s.observe(s.generation);r.busy=True
            s.control('pause')
            self.assertTrue(s.paused);self.assertIsNone(s.task_id);self.assertFalse(s.guarded)
            s.control('resume');self.assertTrue(s.valid(s.generation))
        s.close()
