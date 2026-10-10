import hashlib
import io
import json
import tempfile
import unittest
import urllib.request
from unittest.mock import patch
from pathlib import Path
from arise_app import __version__
from arise_app.updates import validate_manifest, check_update, download_update, MANIFEST_URL
from arise_app.github_access import PrivateRedirect, github_opener

BODY=b'MZ'+b'fixture-installer'*40
MANIFEST={'schema':1,'version':'0.5.0','installer_url':'https://github.com/Maicololiveras/Arise/releases/download/v0.5.0/ARISE-Setup.exe','asset_id':123,'sha256':hashlib.sha256(BODY).hexdigest(),'size':len(BODY),'notes':'Novedades verificadas.'}
class Response(io.BytesIO):
    def geturl(self): return 'https://release-assets.githubusercontent.com/signed-fixture'
class UpdateTests(unittest.TestCase):
    def test_checks_main_with_numeric_version_order_and_shows_notes(self):
        calls=[]
        def opener(request,timeout): calls.append(request);return Response(json.dumps(MANIFEST).encode())
        self.assertEqual(check_update(opener=opener)['notes'],MANIFEST['notes'])
        self.assertIn('ref=main',calls[0].full_url)
        self.assertIsNone(validate_manifest({**MANIFEST,'version':__version__}))
        self.assertIsNotNone(validate_manifest({**MANIFEST,'version':'0.10.0','installer_url':'https://github.com/Maicololiveras/Arise/releases/download/v0.10.0/ARISE-Setup.exe'},'0.9.0'))
    def test_qa_feed_is_separate_and_cross_channel_rejected(self):
        qa={**MANIFEST,'channel':'qa','installer_url':MANIFEST['installer_url'].replace('/v0.5.0/','/qa-v0.5.0/')}
        calls=[]
        def opener(request,timeout):calls.append(request.full_url);return Response(json.dumps(qa).encode())
        self.assertEqual(check_update(opener=opener,channel='qa'),qa)
        self.assertIn('ref=qa',calls[0])
        with self.assertRaises(ValueError):validate_manifest(qa,channel='main')
        with self.assertRaises(ValueError):validate_manifest(MANIFEST,channel='qa')
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(download_update(qa,tmp,lambda *a,**kw:Response(BODY),channel='qa').exists())

    def test_download_verifies_hash_size_and_executable_before_commit(self):
        with tempfile.TemporaryDirectory() as root:
            calls=[]
            def opener(request,timeout):calls.append(request);return Response(BODY)
            file=download_update(MANIFEST,root,opener)
            self.assertEqual(file.read_bytes(),BODY)
            self.assertIn('/releases/assets/123',calls[0].full_url)
            for invalid in (BODY+b'extra', BODY[:-1], b'MZ'+b'X'*(len(BODY)-2)):
                with self.assertRaises(ValueError):download_update(MANIFEST,root,lambda *a,**kw:Response(invalid))
            self.assertEqual(file.read_bytes(),BODY)
            self.assertFalse(file.with_name('ARISE-Setup.download').exists())
    def test_untrusted_url_or_hash_never_launches(self):
        for change in ({'installer_url':'https://evil.example/installer.exe'},{'sha256':''},{'size':True},{'version':'0.5.0-beta'},{'asset_id':-1}):
            with self.assertRaises(ValueError):validate_manifest({**MANIFEST,**change})
    def test_private_redirect_strips_token_from_asset_host(self):
        request=urllib.request.Request('https://api.github.com/repos/owner/repo/releases/assets/123',headers={'Authorization':'Bearer fixture-secret'})
        redirected=PrivateRedirect().redirect_request(request,None,302,'found',{},'https://release-assets.githubusercontent.com/signed')
        self.assertIsNone(redirected.get_header('Authorization'))
        same=PrivateRedirect().redirect_request(request,None,302,'found',{},'https://api.github.com/other')
        self.assertEqual(same.get_header('Authorization'),'Bearer fixture-secret')
        with self.assertRaises(RuntimeError):PrivateRedirect().redirect_request(request,None,302,'found',{},'http://evil.example')
    def test_authenticated_request_refuses_non_github_endpoint(self):
        with self.assertRaises(ValueError):github_opener('fixture-secret')('https://evil.example')
