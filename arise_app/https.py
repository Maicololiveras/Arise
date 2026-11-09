"""Verified HTTPS using the Windows native certificate chain validator."""
import ssl
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse


def tls_context():
    if sys.platform == 'win32':
        import truststore
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    return ssl.create_default_context()


class HTTPSRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        if urlparse(new_url).scheme != 'https':
            raise ValueError('La descarga requiere HTTPS también en sus redirecciones.')
        return super().redirect_request(request, fp, code, message, headers, new_url)


def certificate_error(error):
    reason = getattr(error, 'reason', error)
    return isinstance(reason, ssl.SSLCertVerificationError)


def open_https(request, timeout=30):
    url = request if isinstance(request, str) else request.full_url
    if urlparse(url).scheme != 'https':
        raise ValueError('La descarga requiere HTTPS.')
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=tls_context()), HTTPSRedirect())
    try:
        return opener.open(request, timeout=timeout)
    except (urllib.error.URLError, ssl.SSLError) as error:
        if certificate_error(error):
            raise RuntimeError('No se pudo validar el certificado HTTPS. Revisa la fecha del PC y los certificados de confianza de Windows o del proxy corporativo. Puedes descargar el instalador desde la release oficial con tu navegador. La validación TLS sigue activada.') from error
        raise
