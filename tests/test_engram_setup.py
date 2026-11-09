import hashlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile
from arise_app import engram_setup as e
from arise_app.assistant import Assistant

class EngramSetupTests(unittest.TestCase):
    def release(self):
        base='https://github.com/Gentleman-Programming/engram/releases/download/v3.6.0/'
        return dict(tag_name='v3.6.0',assets=[dict(name=n,browser_download_url=base+n) for n in ['checksums.txt','engram_3.6.0_windows_amd64.zip']])
    def archive(self):
        b=io.BytesIO()
        with zipfile.ZipFile(b,'w') as z:
            z.writestr('engram.exe',b'MZfixture')
            z.writestr('../../do-not-extract',b'foreign')
        data=b.getvalue();sums=(hashlib.sha256(data).hexdigest()+'  engram_3.6.0_windows_amd64.zip\n').encode()
        return data,sums
    def test_release_policy_checksum_and_no_archive_traversal(self):
        version,name,*_=e.release_plan(self.release(),'AMD64')
        data,sums=self.archive()
        self.assertEqual(e.verified_executable(data,sums,name),b'MZfixture')
        with self.assertRaises(ValueError):e.verified_executable(data+b'corrupt',sums,name)
        with self.assertRaises(ValueError):e.release_plan({**self.release(),'prerelease':True},'amd64')
        with self.assertRaises(ValueError):e.release_plan(self.release(),'x86')
        bad=self.release();bad['assets'][1]['browser_download_url']='https://other.test/engram.zip'
        with self.assertRaises(ValueError):e.release_plan(bad,'amd64')
    def test_existing_official_binary_reused_even_with_stale_path(self):
        with tempfile.TemporaryDirectory() as t:
            binary=Path(t)/'engram/bin/engram.exe';binary.parent.mkdir(parents=True);binary.write_bytes(b'MZ')
            env={'LOCALAPPDATA':t,'PATH':'old','ARISE_TOKEN':'fixture'}
            result=e.engine_environment(env,{})
            self.assertEqual(result['ENGRAM_BIN'],str(binary));self.assertEqual(env['PATH'],'old')
            self.assertEqual(result['ARISE_TOKEN'],'fixture')
            with self.assertRaises(RuntimeError):e.engine_environment(env,{'engram_bin':str(Path(t)/'missing.exe')})
    def test_update_adopts_only_after_checksum_and_version_and_preserves_memory(self):
        with tempfile.TemporaryDirectory() as t:
            r=Assistant(t);memory=Path(t)/'memory-kept';memory.write_text('retain')
            data,sums=self.archive()
            def fetch(url,limit):return json.dumps(self.release()).encode() if url==e.API else sums if url.endswith('checksums.txt') else data
            try:
                with patch.object(e,'os',SimpleNamespace(name='nt')),patch.object(e.platform,'machine',return_value='AMD64'),patch.object(e,'fetch',side_effect=fetch),patch.object(e.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='engram 3.6.0\n')):
                    result=e.update_engram(r)
                    self.assertEqual(r.storage.config['engram_bin'],result['binary'])
                    self.assertFalse(result['provider_verified']);self.assertEqual(memory.read_text(),'retain')
                before=r.storage.config['engram_bin']
                with patch.object(e,'os',SimpleNamespace(name='nt')),patch.object(e.platform,'machine',return_value='AMD64'),patch.object(e,'fetch',side_effect=fetch),patch.object(e.subprocess,'run',return_value=SimpleNamespace(returncode=1,stdout='bad')):
                    with self.assertRaises(RuntimeError):e.update_engram(r)
                self.assertEqual(r.storage.config['engram_bin'],before)
            finally:r.close();r.storage.db.close()
