import io
import json
import os
import unittest
from unittest.mock import Mock,patch
from arise_app.desktop_probe import DesktopProbe,SCHEMA
from arise_app.voice_preview import clean_name,transcribe
from arise_app.voice import wake_match

class PreviewTests(unittest.TestCase):
    def test_probe_correlates_inner_id_only(self):
        p=DesktopProbe(Mock());p.request('capabilities')
        key=next(iter(p.pending))
        def deliver(key,data):
            p.widget({'widgetLines':[json.dumps(dict(schema=SCHEMA,kind='response',requestId=key,ok=True,data=data))]})
        deliver('wrong',{'methods':['get_snapshot']})
        self.assertEqual(p.state,{'status':'loading'})
        deliver(key,{'methods':['get_snapshot']})
        deliver(next(iter(p.pending)),{'sequence':17})
        self.assertEqual(p.state,{'status':'ready','methods':['get_snapshot'],'sequence':17})
        self.assertFalse(p.pending)

    def test_ambiguous_ordinary_speech_is_not_an_order(self):
        for text in ('A raíz del informe', 'Hola, a raíz de esto cambiamos'):
            self.assertEqual(clean_name(text),text)
            self.assertFalse(wake_match(text,['hola arise'])[1])
        self.assertEqual(clean_name('Oye, a raíz, abre QA'),'Oye, ARISE, abre QA')

    def test_private_endpoint_requires_tls_and_token(self):
        for url,token in [('http://example.invalid/audio','x'),('https://example.invalid/audio','')]:
            with patch.dict(os.environ,{'ARISE_STT_URL':url,'ARISE_STT_TOKEN':token}),self.assertRaises(ValueError):
                transcribe(bytes(640),'small','es')

    def test_private_stt_upload(self):
        with patch.dict(os.environ,{'ARISE_STT_URL':'https://stt.invalid/v1/audio/transcriptions','ARISE_STT_TOKEN':'test'}),patch('arise_app.voice_preview.build_opener') as make:
            make.return_value.open.return_value=io.BytesIO(b'{"text":"hola"}')
            self.assertEqual(transcribe(bytes(640),'small','es'),'hola')
            req=make.return_value.open.call_args.args[0]
            self.assertIn(b'RIFF',req.data)
            self.assertEqual(req.get_header('Authorization'),'Bearer test')

    def test_echo_filter_preserves_independent_voice(self):
        from arise_app.audio import Audio,resample
        import numpy as np
        import time
        rng=np.random.default_rng(12)
        audio=Audio()
        ref=rng.integers(-1000,1000,size=960,dtype=np.int16).tobytes()
        audio.output_reference.append((time.monotonic(),ref))
        self.assertTrue(audio.playback_echo(resample(ref,24000,16000)[80:720]))
        self.assertFalse(audio.playback_echo(rng.integers(-1000,1000,size=320,dtype=np.int16).tobytes()))

    def test_sentence_spoken_before_completion_without_replaying_it(self):
        import threading
        from types import SimpleNamespace
        from arise_app.local_voice import LocalVoiceBridge
        bridge=LocalVoiceBridge.__new__(LocalVoiceBridge)
        task={'status':'running','voice_partial':'Primera frase. Segunda'}
        bridge.runtime=SimpleNamespace(storage=SimpleNamespace(config={'speech_stream':True}),tasks={'t':task})
        bridge.valid=lambda:True
        bridge.responses=Mock();bridge.responses.empty.return_value=True
        bridge.generation=1;bridge.closed=threading.Event()
        spoken=[]
        def speak(text,epoch):
            spoken.append(text)
            if len(spoken)==1:
                task.update(status='done',output='Primera frase. Segunda frase.')
        bridge.speak=speak
        bridge._wait_result('t',1)
        self.assertEqual(spoken,['Primera frase.','Segunda frase.'])
