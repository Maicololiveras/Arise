import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from arise_app.desktop_layout import DesktopLayout


class LayoutTests(unittest.TestCase):
    def test_acknowledgement_precedes_action_and_cleanup_is_unconditional(self):
        events=[]
        runtime=SimpleNamespace(storage=SimpleNamespace(config={}))
        layout=DesktopLayout(runtime);layout.heartbeat()
        def emit(kind,data):
            events.append(data['action'])
            if data['action']=='prepare':layout.acknowledge(data['id'])
        runtime.emit=emit
        with self.assertRaisesRegex(ValueError,'tool failed'):
            with layout.clear('screenview','capture'):
                events.append('capture');raise ValueError('tool failed')
        self.assertEqual(events,['prepare','capture','done']);self.assertFalse(layout.pending)

    def test_missing_ack_prevents_tool_execution_and_headless_skips(self):
        events=[];runtime=SimpleNamespace(storage=SimpleNamespace(config={}),emit=lambda *args:events.append(args))
        layout=DesktopLayout(runtime)
        with layout.clear('inputcontrol','click'):pass
        self.assertEqual(events,[])
        layout.heartbeat()
        with patch.object(threading.Event,'wait',return_value=False):
            with self.assertRaises(RuntimeError):
                with layout.clear('inputcontrol','click'):self.fail('must not act')
        self.assertEqual([data['action'] for _,data in events],['prepare','done'])
        self.assertFalse(layout.pending)

    def test_stop_during_overlay_handshake_prevents_desktop_action(self):
        import tempfile
        from arise_app.assistant import Assistant
        with tempfile.TemporaryDirectory() as directory:
            runtime=Assistant(directory)
            client=SimpleNamespace(call=__import__('unittest.mock',fromlist=['Mock']).Mock(),close=lambda:None)
            runtime.mcp['screenview']=client
            runtime.desktop_layout.heartbeat()
            original=runtime.emit
            def emit(kind,data):
                original(kind,data)
                if kind=='desktop_layout' and data['action']=='prepare':
                    runtime.stop_generation+=1
                    runtime.desktop_layout.acknowledge(data['id'])
            runtime.emit=emit
            try:
                with self.assertRaisesRegex(RuntimeError,'emergencia'):runtime.call_tool('screenview.capture',{})
                client.call.assert_not_called()
            finally:runtime.mcp.clear();runtime.close();runtime.storage.db.close()
