"""Mobile TOTP verification with a Windows-protected secret and durable throttling."""
import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote
from .storage import Vault


def otp(secret, step):
    raw = hmac.new(base64.b32decode(secret), struct.pack('>Q', step), hashlib.sha1).digest()
    offset = raw[-1] & 15
    return f'{(struct.unpack(">I",raw[offset:offset+4])[0] & 0x7fffffff)%1000000:06d}'


class MobileSecurity:
    def __init__(self, storage, vault=None):
        self.storage = storage
        self.vault = vault or Vault(storage.root, 'mobile-authenticator')
        self.pending = None
        with storage.lock, storage.db:
            storage.db.execute('CREATE TABLE IF NOT EXISTS mobile_auth_state(id INTEGER PRIMARY KEY,last_step INTEGER,failures INTEGER,blocked_until REAL)')
            storage.db.execute('INSERT OR IGNORE INTO mobile_auth_state VALUES(1,-1,0,0)')

    def enabled(self):
        return bool((self.vault.read() or {}).get('secret'))

    def begin(self):
        if self.enabled():
            raise ValueError('El autenticador ya está configurado. Conserva el acceso desde este PC para recuperación.')
        secret = base64.b32encode(secrets.token_bytes(20)).decode()
        self.pending = (secret, time.time()+300)
        return {'secret':secret,'uri':'otpauth://totp/'+quote('ARISE:Mi PC')+'?secret='+secret+'&issuer=ARISE&algorithm=SHA1&digits=6&period=30','expires_in':300}

    def confirm(self, code):
        with self.storage.lock:
            if not self.pending or time.time()>self.pending[1]: raise ValueError('Preparación vencida; vuelve a configurar el autenticador.')
            secret=self.pending[0]
            self._verify(secret,code)
            self.vault.write({'secret':secret})
            self.pending=None
        return {'enabled':True}

    def verify(self, code):
        with self.storage.lock:
            secret=(self.vault.read() or {}).get('secret')
            if not secret: raise PermissionError('Configura el autenticador desde el PC antes de vincular.')
            self._verify(secret,code)

    def _verify(self, secret, code):
        # The caller holds the storage RLock. Failures commit before raising.
        now=time.time()
        row=self.storage.db.execute('SELECT * FROM mobile_auth_state WHERE id=1').fetchone()
        if now<row['blocked_until']: raise PermissionError('Demasiados intentos. Espera cinco minutos.')
        step=int(now//30)
        matched=next((s for s in (step-1,step,step+1) if s>row['last_step'] and isinstance(code,str) and len(code)==6 and code.isascii() and code.isdigit() and hmac.compare_digest(otp(secret,s),code)),None)
        with self.storage.db:
            if matched is None:
                failures=row['failures']+1
                self.storage.db.execute('UPDATE mobile_auth_state SET failures=?,blocked_until=? WHERE id=1',(failures,now+300 if failures>=5 else 0))
            else:
                self.storage.db.execute('UPDATE mobile_auth_state SET last_step=?,failures=0,blocked_until=0 WHERE id=1',(matched,))
        if matched is None: raise PermissionError('Código incorrecto, vencido o ya utilizado. Espera el siguiente código.')
