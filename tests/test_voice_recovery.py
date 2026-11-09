import tempfile
import threading
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch,Mock
from arise_app.voice import VoiceService
from arise_app.audio import Audio
from arise_app.forge_voice import edge_audio

class VoiceRecoveryTests(unittest.TestCase):
    def runtime(self,**config):
        return SimpleNamespace(storage=SimpleNamespace(config={'local_tts':'forge','piper_model':'','voice_windows_fallback':True,**config}),orb=SimpleNamespace(update=Mock()),emit=Mock())

    def test_opt_out_cancel_and_windows_fallback_do_not_speak_twice(self):
        r=self.runtime();voice=VoiceService(r);voice.active.set();voice._sapi=Mock();cancel=threading.Event()
        with patch('arise_app.speech_output.render_edge',side_effect=RuntimeError('Network unavailable')),patch('arise_app.voice.os',SimpleNamespace(name='nt')):
            voice._render_local('Reply',cancel);voice._sapi.assert_called_once_with('Reply',cancel)
            self.assertIn('respaldo',r.emit.call_args.args[1]['text'])
            r.storage.config['voice_windows_fallback']=False
            with self.assertRaises(RuntimeError):voice._render_local('Reply',cancel)
            cancel.set();voice._render_local('Reply',cancel)
            self.assertEqual(voice._sapi.call_count,1)

    def test_preview_opens_only_output_and_honors_selected_device(self):
        r=self.runtime(output_device=7);voice=VoiceService(r)
        with patch('arise_app.voice.Audio') as audio,patch.object(VoiceService,'_render_local') as render:
            result=voice.preview()
            audio.assert_called_once_with(output_device=7);audio.return_value.open_output.assert_called_once();audio.return_value.open.assert_not_called();audio.return_value.close.assert_called_once()
            self.assertTrue(result['played']);render.assert_called_once();self.assertIsNone(voice.preview_voice)
        self.assertIs(r.voice_service,voice)
        output=Mock();capture=Mock()
        with patch.dict('sys.modules',{'sounddevice':SimpleNamespace(RawOutputStream=output,RawInputStream=capture)}):
            a=Audio(output_device=9);a.open_output();a.close();capture.assert_not_called();self.assertEqual(output.call_args.kwargs['device'],9)

    def test_proxy_tls_and_redacted_errors_without_mcp_dependency(self):
        class Process:
            def __init__(self,*a,**kw):self.env=kw['env'];seen.append(self)
            def request(self,*a):raise RuntimeError('Connect Error: 407 https://user:SECRET@proxy.invalid')
            def close(self):pass
        seen=[];active=threading.Event();active.set()
        with tempfile.TemporaryDirectory() as t:
            r=self.runtime(workspace=t)
            with patch('arise_app.forge_voice.JsonProcess',Process),patch('arise_app.forge_voice.edge_bridge_command',return_value=['node','bridge']),patch('urllib.request.getproxies',return_value={'https':'http://user:SECRET@proxy.invalid:80'}),patch('urllib.request.proxy_bypass',return_value=False):
                with self.assertRaises(RuntimeError) as error:edge_audio(r,'Reply',Path(t)/'reply.mp3',threading.Event(),active,threading.Event())
                self.assertNotIn('SECRET',str(error.exception));self.assertIn('proxy',str(error.exception))
                self.assertEqual(seen[0].env['NODE_TLS_REJECT_UNAUTHORIZED'],'1')
                self.assertEqual(seen[0].env['ARISE_SPEECH_PROXY'],'http://user:SECRET@proxy.invalid:80')
