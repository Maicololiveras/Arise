import ssl
import unittest
import urllib.error
import urllib.request
from types import SimpleNamespace
from unittest.mock import Mock, patch
from arise_app.https import tls_context, open_https, HTTPSRedirect


class HTTPSTests(unittest.TestCase):
    def test_windows_uses_native_verifier_with_client_validation(self):
        factory=Mock(return_value=object())
        with patch('arise_app.https.sys.platform','win32'), patch.dict('sys.modules',{'truststore':SimpleNamespace(SSLContext=factory)}):
            self.assertIs(tls_context(),factory.return_value)
        factory.assert_called_once_with(ssl.PROTOCOL_TLS_CLIENT)

    def test_other_platforms_keep_certificate_and_hostname_validation(self):
        with patch('arise_app.https.sys.platform','linux'):
            context=tls_context()
        self.assertEqual(context.verify_mode,ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)

    def test_certificate_failure_does_not_retry_without_validation(self):
        transport=Mock();transport.open.side_effect=urllib.error.URLError(ssl.SSLCertVerificationError(1,'certificate verify failed'))
        with patch('arise_app.https.urllib.request.build_opener',return_value=transport):
            with self.assertRaisesRegex(RuntimeError,'certificados de confianza'):
                open_https('https://example.com')
        self.assertEqual(transport.open.call_count,1)

    def test_http_and_downgrade_redirect_are_rejected(self):
        with self.assertRaises(ValueError):open_https('http://example.com')
        with self.assertRaises(ValueError):
            HTTPSRedirect().redirect_request(urllib.request.Request('https://example.com'),None,302,'redirect',{},'http://example.com/file')

    def test_transport_preserves_timeout_and_returns_stream(self):
        transport=Mock()
        with patch('arise_app.https.urllib.request.build_opener',return_value=transport):
            self.assertIs(open_https('https://example.com',timeout=7),transport.open.return_value)
        transport.open.assert_called_once_with('https://example.com',timeout=7)

    @unittest.skipUnless(__import__('sys').platform == 'win32', 'Native Windows certificate store')
    def test_native_windows_context_keeps_validation_enabled(self):
        import truststore
        context=tls_context()
        self.assertIsInstance(context,truststore.SSLContext)
        self.assertEqual(context.verify_mode,ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)
