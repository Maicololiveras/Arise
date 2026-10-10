import tempfile
import unittest
import zipfile
from pathlib import Path
from arise_app.downloads import safe_extract
from arise_app.downloads import install_voice_pack
import hashlib
import json
class DownloadTests(unittest.TestCase):
    def test_zip_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            archive=Path(root)/'bad.zip'
            with zipfile.ZipFile(archive,'w') as z:z.writestr('../outside','bad')
            with self.assertRaises(ValueError):safe_extract(archive,Path(root)/'model')
            self.assertFalse((Path(root)/'outside').exists())

    def test_voice_zip_installs_and_tampered_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            root=Path(root); archive=root/'voice.zip'
            files={'models/vosk-model-small-es-0.42/am/final.mdl':b'fixture','models/vosk-model-small-es-0.42/conf/model.conf':b'fixture'}
            manifest={'format':'arise-voice-pack-v1','files':{p:hashlib.sha256(b).hexdigest() for p,b in files.items()}}
            with zipfile.ZipFile(archive,'w') as z:
                for p,b in files.items(): z.writestr(p,b)
                z.writestr('manifest.json',json.dumps(manifest))
            target=install_voice_pack(archive,root/'data'); self.assertTrue((Path(target)/'am/final.mdl').is_file())
            self.assertEqual(install_voice_pack(archive,root/'data'),target)
            with zipfile.ZipFile(root/'tampered.zip','w') as z:
                for p,b in files.items():z.writestr(p,b'changed')
                z.writestr('manifest.json',json.dumps(manifest))
            with self.assertRaises(ValueError):install_voice_pack(root/'tampered.zip',root/'second')
