"""Deterministic latency safeguards; no microphone, network or timing targets."""
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import numpy as np
from arise_app.turn_detection import TurnDetector
from arise_app.forge_voice import EdgeAudioSession, edge_audio
from arise_app.voice_metrics import VoiceTrace, current_trace

class VoicePerformanceTests(unittest.TestCase):
    def test_trim_keeps_internal_pauses_and_final_margin(self):
        voice=(np.ones(320,dtype='<i2')*1000).tobytes()
        quiet=bytes(640)
        detector=TurnDetector(1400)
        blocks=[voice]*20+[quiet]*35+[voice]*20+[quiet]*70
        result=None
        for block in blocks:
            _,turn=detector.feed(block)
            if turn is not None:
                self.assertIsNone(result)
                result=turn
        self.assertEqual(result,b''.join(blocks[:-60]))
        self.assertEqual(detector.last_endpoint_ms,1400)
        self.assertEqual(detector.last_capture_ms-len(result)/32,1200)
        self.assertFalse(detector.started)

    def test_noise_without_sustained_speech_produces_no_turn(self):
        detector=TurnDetector()
        loud=(np.ones(320,dtype='<i2')*1000).tobytes()
        for block in [loud,bytes(640)]*100:
            self.assertIsNone(detector.feed(block)[1])

    def test_maximum_turn_preserves_voiced_tail(self):
        detector=TurnDetector()
        loud=(np.ones(320,dtype='<i2')*1000).tobytes()
        for _ in range(1600):
            _,turn=detector.feed(loud)
            if turn is not None:break
        self.assertEqual(turn[-len(loud):],loud)
        self.assertEqual(detector.last_endpoint_ms,0)

    def test_response_reuses_process_and_closes_once(self):
        active=threading.Event();active.set()
        runtime=SimpleNamespace(storage=SimpleNamespace(config={'workspace':'.'}))
        process=Mock()
        with tempfile.TemporaryDirectory() as tmp, patch('arise_app.forge_voice.JsonProcess',return_value=process) as spawn, patch('arise_app.forge_voice.edge_bridge_command',return_value=['node','bridge']), patch('urllib.request.getproxies',return_value={}):
            with EdgeAudioSession() as session:
                for i in range(3):
                    self.assertTrue(edge_audio(runtime,'Hello',Path(tmp)/f'{i}.mp3',threading.Event(),active,threading.Event(),session=session))
                process.close.assert_not_called()
            self.assertEqual(spawn.call_count,1)
            self.assertEqual(process.request.call_count,3)
            process.close.assert_called_once()

    def test_cancel_closes_inflight_process(self):
        active=threading.Event();active.set();cancel=threading.Event()
        entered=threading.Event();released=threading.Event()
        process=Mock()
        def request(*args):entered.set();released.wait(2)
        process.request.side_effect=request
        process.close.side_effect=released.set
        runtime=SimpleNamespace(storage=SimpleNamespace(config={'workspace':'.'}))
        with patch('arise_app.forge_voice.JsonProcess',return_value=process),patch('arise_app.forge_voice.edge_bridge_command',return_value=['node','bridge']),patch('urllib.request.getproxies',return_value={}):
            result=[]
            with EdgeAudioSession() as session:
                worker=threading.Thread(target=lambda:result.append(edge_audio(runtime,'Hello',Path('/tmp/test.mp3'),cancel,active,threading.Event(),session=session)))
                worker.start();self.assertTrue(entered.wait(1));cancel.set();worker.join(1)
                self.assertFalse(worker.is_alive());self.assertEqual(result,[False]);self.assertTrue(released.is_set())

    def test_monotonic_content_free_metrics_and_context_cleanup(self):
        runtime=SimpleNamespace(emit=Mock())
        with patch('arise_app.voice_metrics.time.monotonic',side_effect=[10,10.25]):
            trace=VoiceTrace(runtime)
            with trace.activate():
                self.assertIs(current_trace(),trace)
                trace.record('transcription',trace.started)
        self.assertIsNone(current_trace())
        kind,data=runtime.emit.call_args.args
        self.assertEqual(kind,'voice_metrics');self.assertEqual(data['duration_ms'],250)
        self.assertEqual(set(data),{'turn_id','stage','duration_ms'})

    def test_runtime_keeps_only_bounded_recent_metrics(self):
        from collections import deque
        from arise_app.runtime import Runtime
        runtime=Runtime.__new__(Runtime)
        runtime.lock=threading.RLock();runtime.sequence=0
        runtime.events=deque(maxlen=4000);runtime.voice_metrics=deque(maxlen=120)
        runtime.event_ready=threading.Condition(runtime.lock)
        runtime.conversation='test'
        for number in range(150):
            runtime.emit('voice_metrics',{'turn_id':str(number),'stage':'transcription','duration_ms':1})
        snapshot=runtime.voice_timing_snapshot()
        self.assertEqual(len(snapshot),120)
        self.assertEqual(snapshot[0]['turn_id'],'30')
        self.assertEqual(snapshot[-1]['turn_id'],'149')

    def test_warm_voice_session_keeps_recognizer_until_model_changes(self):
        from arise_app.voice import VoiceService
        runtime=SimpleNamespace(storage=SimpleNamespace(config={'voice_timeout':30}),emit=Mock(),orb=SimpleNamespace(update=Mock()))
        service=VoiceService(runtime)
        bridge=Mock();bridge.valid.return_value=False
        model=Mock();recognizer=Mock()
        vosk=SimpleNamespace(Model=model,KaldiRecognizer=recognizer,SetLogLevel=Mock())
        with patch.dict('sys.modules',{'vosk':vosk}),patch('arise_app.models.resolve_stt',side_effect=[('vosk','a'),('vosk','a'),('vosk','b')]),patch('arise_app.hardware.local_profile',return_value='light'),patch('arise_app.local_voice.LocalVoiceBridge',return_value=bridge):
            service._local('hello')
            service._local('hello')
            self.assertEqual(model.call_count,1)
            service._local('hello')
            self.assertEqual(model.call_count,2)
        reused=[call.args[1]['reused'] for call in runtime.emit.call_args_list if call.args[0]=='voice_metrics']
        self.assertEqual(reused,[False,True,False])
