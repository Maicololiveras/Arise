import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from arise_app.offline_pack import extract_verified, _install
from arise_app.runtime import Runtime


def make_pack(path, corrupt=False, extra=None):
    files={'server/llama-server.exe':b'MZfixture','models/dialogue.gguf':b'GGUFfixture',
        'models/small.pt':b'checkpoint','models/vosk-model-small-es-0.42/am/final.mdl':b'weights',
        'models/vosk-model-small-es-0.42/conf/model.conf':b'config'}
    if extra:files[extra]=b'bad'
    manifest={'format':'arise-offline-pack-v1','platform':'windows-x64','server':'server/llama-server.exe',
        'files':{name:hashlib.sha256(data).hexdigest() for name,data in files.items()}}
    if corrupt:files['models/small.pt']=b'corrupted'
    with zipfile.ZipFile(path,'w') as archive:
        archive.writestr('manifest.json',json.dumps(manifest))
        for name,data in files.items():archive.writestr(name,data)


class OfflinePackTests(unittest.TestCase):
    def test_extracts_complete_verified_pack(self):
        with tempfile.TemporaryDirectory() as root:
            root=Path(root);make_pack(root/'models.zip');(root/'out').mkdir()
            manifest=extract_verified(root/'models.zip',root/'out')
            self.assertEqual((root/'out/models/small.pt').read_bytes(),b'checkpoint')
            self.assertEqual(manifest['server'],'server/llama-server.exe')

    def test_rejects_corruption_traversal_and_windows_paths(self):
        for extra,corrupt in [(None,True),('../escape',False),('server\\escape',False),('server/C:stream',False)]:
            with self.subTest(extra=extra),tempfile.TemporaryDirectory() as root:
                root=Path(root);make_pack(root/'models.zip',corrupt=corrupt,extra=extra);(root/'out').mkdir()
                with self.assertRaises(ValueError):extract_verified(root/'models.zip',root/'out')
                self.assertFalse((root/'escape').exists())

    def test_success_configures_all_paths_without_changing_agent_or_microphone(self):
        with tempfile.TemporaryDirectory() as root:
            root=Path(root);make_pack(root/'models.zip');runtime=Runtime(root/'data')
            runtime.storage.config.update(agent_model='keep-this',wake_enabled=False)
            try:
                with patch('arise_app.offline_pack.probe_voice'),patch('arise_app.local_dialogue.LocalDialogue') as dialogue:
                    dialogue.return_value.request.return_value={'choices':[{'message':{'content':'Listo.'}}]}
                    result=_install(runtime,root/'models.zip')
                config=runtime.storage.config
                self.assertEqual(result['inference'],'passed')
                self.assertEqual(config['agent_model'],'keep-this')
                self.assertTrue(config['onboarding_complete'])
                self.assertFalse(config['wake_enabled'])
                self.assertTrue(Path(config['local_stt_model']).is_file())
                self.assertTrue(Path(config['local_server_command'][0]).is_file())
                self.assertEqual(config['local_stt_engine'],'openai-whisper')
            finally:runtime.close();runtime.storage.db.close()

    def test_failed_inference_restores_existing_settings_and_removes_staging(self):
        with tempfile.TemporaryDirectory() as root:
            root=Path(root);make_pack(root/'models.zip');runtime=Runtime(root/'data')
            before=json.loads(json.dumps(runtime.storage.config))
            try:
                with patch('arise_app.offline_pack.probe_voice'),patch('arise_app.local_dialogue.LocalDialogue',side_effect=RuntimeError('unavailable')):
                    with self.assertRaisesRegex(RuntimeError,'unavailable'):_install(runtime,root/'models.zip')
                self.assertEqual(runtime.storage.config,before)
                self.assertEqual(list((root/'data/offline').iterdir()),[])
            finally:runtime.close();runtime.storage.db.close()
