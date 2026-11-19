import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from arise_app.assistant import Assistant


class IdleEngineTests(unittest.TestCase):
    def test_only_checkpoint_and_release_known_idle_chat(self):
        with tempfile.TemporaryDirectory() as root:
            r = Assistant(root)
            session = Path(root)/'session.jsonl'; session.touch()
            proc = Mock(); proc.request.return_value = {'data':dict(isStreaming=False,isCompacting=False,pendingMessageCount=0,messageCount=2,sessionFile=str(session))}
            r.pi=proc
            try:
                r.engine_last_use=time.monotonic()-700
                self.assertFalse(r.release_idle_engine())
                r.storage.config['light_mode']=True
                self.assertFalse(r.release_idle_engine())  # upstream jobs not known
                r.desktop_probe=SimpleNamespace(state={'jobs':0,'status':'ready'})
                r.dialogs['question']={}
                self.assertFalse(r.release_idle_engine())
                r.dialogs.clear()
                r.terminals.jobs['pending']={'process':Mock(poll=lambda:None)}
                self.assertFalse(r.release_idle_engine())
                r.terminals.jobs.clear()
                proc.request.assert_not_called()
                self.assertTrue(r.release_idle_engine())
                proc.close.assert_called_once()
                self.assertIsNone(r.pi)
                self.assertEqual(r.storage.conversations()[0]['pi_file'],str(session))
            finally:
                r.pi=None;r.terminals.jobs.clear();r.close();r.storage.db.close()
