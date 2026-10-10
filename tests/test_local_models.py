import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from arise_app.models import discover_voice_models, resolve_stt
from arise_app.voice import VoiceService

class LocalModelTests(unittest.TestCase):
    def test_detects_user_formats_and_resolves_existing_models_without_downloads(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root); home = root / 'home'; cache = home / '.cache/whisper'; cache.mkdir(parents=True)
            (cache / 'base.pt').write_bytes(b'fixture')
            models = root / 'whisper_models'; base = models / 'base'; base.mkdir(parents=True)
            (base / 'model.bin').write_bytes(b'fixture'); (base / 'config.json').write_text('{}')
            detected = discover_voice_models(home, [models])
            self.assertEqual({m['engine'] for m in detected}, {'openai-whisper', 'faster-whisper'})
            self.assertEqual(resolve_stt({'local_stt_engine':'auto','local_stt_model':str(base)}), ('faster-whisper',str(base)))
            self.assertEqual(resolve_stt({'local_stt_engine':'auto','local_stt_model':str(cache/'base.pt')}), ('openai-whisper',str(cache/'base.pt')))
            with self.assertRaises(RuntimeError): resolve_stt({'local_stt_engine':'faster-whisper','local_stt_model':str(cache/'base.pt')})
            with self.assertRaises(RuntimeError): resolve_stt({'local_stt_engine':'openai-whisper','local_stt_model':str(base)})

    def test_auto_uses_packaged_vosk_when_no_whisper_files_exist(self):
        with tempfile.TemporaryDirectory() as root:
            model = Path(root) / 'vosk'; (model/'am').mkdir(parents=True); (model/'conf').mkdir()
            (model/'am/final.mdl').write_bytes(b'fixture'); (model/'conf/model.conf').write_text('fixture')
            with patch('arise_app.models.discover_voice_models', return_value=[]):
                self.assertEqual(resolve_stt({'local_stt_engine':'auto','local_stt_model':'','wake_model':str(model)}), ('vosk',str(model)))

    def test_local_transcription_preserves_each_engine_contract(self):
        runtime=SimpleNamespace(); service=VoiceService(runtime); pcm=bytes(320)
        service.whisper=Mock(); service.whisper.FinalResult.return_value=json.dumps({'text':'hola arise'})
        self.assertEqual(service.transcribe_local(pcm,'vosk'), 'hola arise')
        service.whisper.AcceptWaveform.assert_called_once_with(pcm)
        service.whisper=Mock(); service.whisper.transcribe.return_value={'text':' texto pt '}
        self.assertEqual(service.transcribe_local(pcm,'openai-whisper'),'texto pt')
        self.assertEqual(service.whisper.transcribe.call_args.kwargs, {'language':'es','fp16':False})
        service.whisper=Mock(); service.whisper.transcribe.return_value=([SimpleNamespace(text='hola'),SimpleNamespace(text='modelo')],None)
        self.assertEqual(service.transcribe_local(pcm,'faster-whisper'),'hola modelo')
