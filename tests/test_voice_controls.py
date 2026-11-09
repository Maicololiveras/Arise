import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from arise_app.voice_controls import command, dispatch
from arise_app.local_voice import LocalVoiceBridge
from arise_app.voice import VoiceService

class VoiceControlTests(unittest.TestCase):
    def test_exact_phrases_accents_and_wake_prefix(self):
        for text, expected in [('¡Ari, apágate!', 'shutdown'),('ARISE, stop listening.', 'end'),('silencio','speech'),('cancel task','stop'),('modo cuestionario','study_start')]:
            self.assertEqual(command(text),expected)
        for text in ['no te apagues','escribe apágate en un archivo','say stop task','cancela la tarea de mañana y crea otra']:
            self.assertIsNone(command(text))
    def test_controls_do_not_cross_chat_and_end_does_not_stop_task(self):
        r=SimpleNamespace(conversation='a',chat_generation=1,emit=Mock(),stop=Mock(),request_shutdown=Mock())
        end=Mock();interrupt=Mock()
        self.assertTrue(dispatch(r,'deja de escuchar','a',1,interrupt,end))
        end.assert_called_once();r.stop.assert_not_called()
        dispatch(r,'apágate','old',0,interrupt,end);r.request_shutdown.assert_not_called()
        dispatch(r,'Ari apágate','a',1,interrupt,end);r.request_shutdown.assert_called_once()
    def test_stop_bypasses_blocked_dialogue_worker(self):
        active=threading.Event();active.set();release=threading.Event();entered=threading.Event()
        r=SimpleNamespace(conversation='a',chat_generation=0,storage=SimpleNamespace(config={}),tasks={},dialogs={},emit=Mock(),stop=Mock())
        def slow(text): entered.set();release.wait(2);return {'task_id':'x'}
        r.steer=slow
        bridge=LocalVoiceBridge(r,SimpleNamespace(interrupt=Mock()),Mock(),active,threading.Event())
        try:
            bridge.submit('hello');self.assertTrue(entered.wait(1))
            bridge.submit('Ari cancela la tarea');r.stop.assert_called_once()
        finally:release.set();bridge.close()
    def test_end_discards_pending_wake(self):
        r=SimpleNamespace()
        voice=VoiceService(r);voice.wakes.put('hello');voice.active.set()
        voice.end_session()
        self.assertTrue(voice.wakes.empty());self.assertFalse(voice.active.is_set())
    def test_shutdown_stops_work_and_notifies_renderer_once(self):
        import tempfile
        from arise_app.assistant import Assistant
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            r=Assistant(directory)
            try:
                r.voice_service=Mock();callback=Mock();r.shutdown_callback=callback
                with patch.object(threading.Timer,'start') as start, patch.object(r,'stop') as stop:
                    r.request_shutdown();r.request_shutdown()
                    stop.assert_called_once();start.assert_called_once()
                self.assertTrue(r.shutdown_requested)
                self.assertTrue(any(e['kind']=='shutdown_requested' for e in r.events_after(0)['events']))
            finally:r.voice_service=None;r.close();r.storage.db.close()
