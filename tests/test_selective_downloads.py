import hashlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import zipfile
from arise_app.public_tools import install_public_tool, BASE
from arise_app.tool_setup import _install
from arise_app.model_setup import _install as install_models


def runtime(root):
    config={'mcp':{'custom':{'command':['keep'], 'enabled':False}}}
    value=SimpleNamespace(storage=SimpleNamespace(root=root,config=config),mcp={},emit=Mock(),credentials=Mock(),model_service=Mock())
    value.settings=lambda changes:config.update(changes)
    def connect(name):
        value.mcp[name]=Mock(tools=[{'name':'test'}]);return value.mcp[name]
    value.connect_mcp=connect
    return value


class PublicDownloadTests(unittest.TestCase):
    def fixture(self, members=None):
        data=io.BytesIO()
        with zipfile.ZipFile(data,'w') as z:
            for path,body in (members or {'forge-mcp.exe':b'MZfixture'}).items():z.writestr(path,body)
        payload=data.getvalue();tag='herramientas-forge-v0.1.0-'+'a'*12
        manifest={'schema':1,'tool':'forge','platform':'windows-x64','tag':tag,'entry':'forge-mcp.exe','size':len(payload),'sha256':hashlib.sha256(payload).hexdigest(),'url':f'https://github.com/Maicololiveras/Arise/releases/download/{tag}/forge-mcp-windows-x64.zip'}
        return payload,manifest

    def download(self, root, payload, manifest):
        def opener(url, **kwargs):
            self.assertIsInstance(url,str) # No authenticated Request objects.
            return io.BytesIO(json.dumps(manifest).encode() if url==BASE+'forge.json' else payload)
        return install_public_tool('forge',root,opener=opener)

    def test_public_download_requires_no_credentials(self):
        payload,manifest=self.fixture()
        with tempfile.TemporaryDirectory() as temp:
            spec,_=self.download(temp,payload,manifest)
            self.assertEqual(Path(spec['command'][0]).read_bytes(),b'MZfixture')
            self.assertFalse((Path(temp)/'forge.zip').exists())

    def test_rejects_pending_corrupt_and_external_downloads(self):
        payload,manifest=self.fixture()
        for changes,pattern in [({'status':'pending'},'no está publicado'),({'sha256':'0'*64},'SHA-256'),({'url':'https://example.com/file.zip'},'Origen')]:
            with self.subTest(changes=changes),tempfile.TemporaryDirectory() as temp:
                with self.assertRaisesRegex(RuntimeError,pattern):self.download(temp,payload,{**manifest,**changes})
                self.assertFalse((Path(temp)/'forge/forge-mcp.exe').exists())

    def test_rejects_unsafe_zip_before_extraction(self):
        for path in ('../escape.exe','CON.exe','dir/../escape','forge-mcp.EXE'):
            payload,manifest=self.fixture({'forge-mcp.exe':b'MZ',path:b'unsafe'})
            with self.subTest(path=path),tempfile.TemporaryDirectory() as temp:
                with self.assertRaisesRegex(RuntimeError,'ZIP inválido'):self.download(temp,payload,manifest)
                self.assertFalse((Path(temp)/'forge').exists())

    def test_single_tool_preserves_other_configuration(self):
        with tempfile.TemporaryDirectory() as temp:
            rt=runtime(Path(temp))
            with patch('arise_app.public_tools.install_public_tool',return_value=({'command':['screenview.exe'],'enabled':True},{'tool':'screenview'})) as download,patch('arise_app.tool_setup.github_token',side_effect=AssertionError('must not authenticate')):
                result=_install(rt,['screenview'])
            self.assertEqual(download.call_count,1)
            self.assertEqual(result['catalogs'],{'screenview':1})
            self.assertEqual(rt.storage.config['mcp']['custom']['command'],['keep'])
            self.assertNotIn('forge',rt.storage.config['mcp'])

    def test_failed_catalog_restores_settings_and_closes_new_process(self):
        with tempfile.TemporaryDirectory() as temp:
            rt=runtime(Path(temp));old=json.loads(json.dumps(rt.storage.config));client=Mock(tools=[])
            def connect(name):rt.mcp[name]=client;return client
            rt.connect_mcp=connect
            with patch('arise_app.public_tools.install_public_tool',return_value=({'command':['screenview.exe'],'enabled':True},{})):
                with self.assertRaisesRegex(RuntimeError,'vacío'):_install(rt,['screenview'])
            client.close.assert_called_once()
            self.assertEqual(rt.storage.config,old)
            self.assertEqual(list((Path(temp)/'tools').iterdir()),[])

    def test_pending_download_does_not_change_running_tools(self):
        with tempfile.TemporaryDirectory() as temp:
            rt=runtime(Path(temp));client=Mock();rt.mcp['forge']=client
            with patch('arise_app.public_tools.install_public_tool',side_effect=RuntimeError('pending')):
                with self.assertRaisesRegex(RuntimeError,'pending'):_install(rt,['forge'])
            client.close.assert_not_called()
            self.assertEqual(list((Path(temp)/'tools').iterdir()),[])

    def test_models_configure_only_selected_group(self):
        with tempfile.TemporaryDirectory() as temp:
            rt=runtime(Path(temp));rt.storage.config['local_stt_engine']='existing'
            with patch('arise_app.model_setup.prepare_model',return_value={'wake_model':'downloaded-vosk'}) as prepare:
                install_models(rt,['vosk'])
            self.assertEqual(prepare.call_count,1)
            self.assertEqual(rt.storage.config['wake_model'],'downloaded-vosk')
            self.assertEqual(rt.storage.config['local_stt_engine'],'existing')

    def test_model_failure_preserves_configuration_and_cleans_downloads(self):
        with tempfile.TemporaryDirectory() as temp:
            rt=runtime(Path(temp));before=json.loads(json.dumps(rt.storage.config))
            with patch('arise_app.model_setup.prepare_model',side_effect=[{'wake_model':'new'},RuntimeError('checksum')]):
                with self.assertRaisesRegex(RuntimeError,'checksum'):install_models(rt,['vosk','whisper'])
            self.assertEqual(rt.storage.config,before)
            self.assertEqual(list((Path(temp)/'models').iterdir()),[])

    def test_existing_forge_voice_bridge_survives_public_upgrade(self):
        from arise_app.forge_voice import voice_command
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);rt=runtime(root)
            node=root/'node.exe';node.touch()
            entry=root/'old/dist/bin/forge-mcp-cli.js';entry.parent.mkdir(parents=True);entry.touch()
            voice=root/'old/dist/voice/forge-voice.js';voice.parent.mkdir();voice.touch()
            rt.storage.config['mcp']['forge']={'command':[str(node),str(entry)],'enabled':True}
            with patch('arise_app.public_tools.install_public_tool',return_value=({'command':['public-forge.exe'],'enabled':True},{})):
                _install(rt,['forge'])
            self.assertEqual(voice_command(rt),[str(node),str(voice)])

    def test_dialogue_probe_failure_restores_previous_settings(self):
        with tempfile.TemporaryDirectory() as temp:
            rt=runtime(Path(temp));rt.storage.config['local_dialogue_url']='http://127.0.0.1:8080/v1';before=json.loads(json.dumps(rt.storage.config))
            with patch('arise_app.model_setup.prepare_model',return_value={'local_dialogue_url':'new'}),patch('arise_app.local_dialogue.LocalDialogue',side_effect=RuntimeError('server failed')):
                with self.assertRaisesRegex(RuntimeError,'server failed'):install_models(rt,['dialogue'])
            self.assertEqual(rt.storage.config,before)
            rt.model_service.close.assert_called_once()

    def test_pinned_model_checksum_failure_is_not_activated(self):
        from arise_app.model_setup import download_file
        with tempfile.TemporaryDirectory() as temp,patch('arise_app.model_setup.urllib.request.urlopen',return_value=io.BytesIO(b'corrupt')):
            with self.assertRaisesRegex(RuntimeError,'SHA-256'):download_file('models/small.pt',Path(temp)/'small.pt',Mock())
