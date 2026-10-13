import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
import numpy as np
from arise_app.turn_detection import TurnDetector
from arise_app.assistant import Assistant
from arise_app.user_errors import friendly_error

class UsabilityTests(unittest.TestCase):
    def test_natural_pause_old_detector_splits_new_detector_keeps_sentence(self):
        voiced=(np.ones(320,dtype='<i2')*1000).tobytes();quiet=bytes(640)
        blocks=[voiced]*20+[quiet]*35+[voiced]*20+[quiet]*80
        results=[]
        for pause in (500,1400):
            detector=TurnDetector(pause);results.append(sum(detector.feed(block)[1] is not None for block in blocks))
        self.assertEqual(results,[2,1])
    def test_stop_closes_observers_before_waiting_for_agent_and_blocks_reconnect(self):
        with tempfile.TemporaryDirectory() as root:
            r=Assistant(root);calls=[]
            for name in ('inputcontrol','screenview','forge'):
                process=SimpleNamespace(poll=lambda:0)
                rpc=SimpleNamespace(process=process,request=lambda *a,**k:None)
                r.mcp[name]=SimpleNamespace(rpc=rpc,close=lambda n=name:calls.append(n))
            r.stop();self.assertCountEqual(calls,['inputcontrol','screenview','forge'])
            self.assertFalse(r.desktop);self.assertTrue(r.desktop_halted)
            with self.assertRaises(RuntimeError):r.connect_mcp('screenview')
            with self.assertRaises(RuntimeError):r.call_tool('screenview.screen_capture',{})
            r.close();r.storage.db.close()
    def test_inflight_connection_cannot_survive_stop(self):
        with tempfile.TemporaryDirectory() as root:
            r=Assistant(root);entered=threading.Event();release=threading.Event();errors=[]
            client=Mock();client.tools=[]
            def connect(*a,**kw):entered.set();release.wait(2);return client
            def work():
                try:r.connect_mcp('screenview')
                except Exception as e:errors.append(str(e))
            with patch('arise_app.runtime.McpClient',side_effect=connect):
                t=threading.Thread(target=work);t.start();self.assertTrue(entered.wait(1));r.stop();release.set();t.join(2)
            client.close.assert_called_once();self.assertNotIn('screenview',r.mcp);self.assertTrue(errors)
            r.close();r.storage.db.close()
    def test_503_is_explained_without_retry(self):
        self.assertIn('No se reenvió',friendly_error('HTTP Error 503: Service Unavailable'))
    def test_forge_edge_contract_with_real_node_adapter(self):
        import subprocess,shutil
        from pathlib import Path
        subprocess.run([shutil.which('node'),'--test',str(Path(__file__).with_name('forge-edge.test.mjs'))],check=True,capture_output=True)
