import threading
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from arise_app.speech_output import speech_chunks,render_edge


class SpeechOutputTests(unittest.TestCase):
    def test_chunks_preserve_words_and_have_bounded_initial_latency(self):
        text='Hola. ¿Cómo estás? '+('Esta es una frase con palabras. '*100)
        parts=speech_chunks(text)
        self.assertEqual(' '.join(parts),' '.join(text.split()))
        self.assertLessEqual(len(parts[0]),180)
        self.assertTrue(all(len(part)<=360 for part in parts))

    def test_prefetch_is_ordered_and_partial_failure_cannot_repeat_reply(self):
        active=threading.Event();active.set();cancel=threading.Event();spoken=[]
        audio=SimpleNamespace(speaking=False,play=lambda data,rate:spoken.append(data),interrupt=Mock())
        voice=SimpleNamespace(active=active,shutdown=threading.Event(),audio=audio,runtime=SimpleNamespace(storage=SimpleNamespace(config={}),orb=SimpleNamespace(update=Mock())))
        calls=[]
        def synth(runtime,text,path,*args):
            calls.append(text)
            if len(calls)==2:raise RuntimeError('second phrase failed')
            path.write_bytes(b'mp3');return True
        class Process:
            returncode=0
            def __init__(self,args,**kwargs):
                with wave.open(str(args[-1]),'wb') as f:
                    f.setnchannels(1);f.setsampwidth(2);f.setframerate(24000);f.writeframes(b'\0\0'*20)
            def poll(self):return 0
        with patch.dict('sys.modules', {'miniaudio': None}), patch('arise_app.forge_voice.edge_audio',side_effect=synth),patch('arise_app.speech_output.shutil.which',return_value='ffmpeg'),patch('arise_app.speech_output.subprocess.Popen',Process):
            with self.assertRaises(RuntimeError) as caught:render_edge(voice,'Una frase. '*70,cancel)
        self.assertTrue(caught.exception.audio_started);self.assertEqual(len(spoken),1);self.assertEqual(len(calls),2)
