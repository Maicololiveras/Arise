import base64
import copy
import io
import tempfile
import time
import unittest
import wave
from types import SimpleNamespace
from unittest.mock import Mock,patch
from arise_app.storage import Storage
from arise_app.mobile_security import MobileSecurity,otp
from arise_app.mobile_setup import prepare,save_settings,resume
from arise_app.mobile_voice import transcribe

class Vault:
    def __init__(self):self.data={}
    def read(self):return copy.deepcopy(self.data)
    def write(self,data):self.data=copy.deepcopy(data)

class MobileTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.storage=Storage(self.temp.name)
        self.vault=Vault();self.security=MobileSecurity(self.storage,self.vault)
    def tearDown(self):self.storage.db.close();self.temp.cleanup()
    def test_rfc6238_vector(self):
        secret=base64.b32encode(b'12345678901234567890').decode()
        self.assertEqual(otp(secret,59//30),'287082')
    def test_enrollment_replay_expiry_and_persistent_throttle(self):
        with patch('arise_app.mobile_security.time.time',return_value=100000):
            with self.assertRaises(PermissionError):self.security.verify('123456')
            secret=self.security.begin()['secret'];code=otp(secret,100000//30)
            self.security.confirm(code);self.assertTrue(self.security.enabled())
            with self.assertRaises(PermissionError):self.security.verify(code)
            for _ in range(4):
                with self.assertRaises(PermissionError):self.security.verify('bad')
        restarted=MobileSecurity(self.storage,self.vault)
        with patch('arise_app.mobile_security.time.time',return_value=100030):
            with self.assertRaises(PermissionError):restarted.verify(otp(secret,100030//30))
        with patch('arise_app.mobile_security.time.time',return_value=100400):restarted.verify(otp(secret,100400//30))
        self.assertNotIn(secret,(self.storage.root/'settings.json').read_text())
    def test_setup_refuses_other_services_and_funnel(self):
        runtime=SimpleNamespace(storage=self.storage,mobile_security=Mock(enabled=Mock(return_value=True)),mobile_server=None,start_mobile=Mock(),stop_mobile=Mock())
        status='{"BackendState":"Running","Self":{"DNSName":"pc.tail.ts.net."}}'
        for existing in ('{"TCP":{"443":{}}}', '{"AllowFunnel":{"pc.tail.ts.net:443":true}}'):
            with patch('arise_app.mobile_setup.cli',side_effect=[status,existing]) as command:
                with self.assertRaises(RuntimeError):prepare(runtime)
                self.assertEqual(command.call_count,2)
        runtime.start_mobile.assert_not_called()
    def test_setup_and_restart_keep_same_port(self):
        runtime=SimpleNamespace(storage=self.storage,mobile_security=Mock(enabled=Mock(return_value=True)),mobile_server=None)
        def start(origin,port=0):runtime.mobile_server=SimpleNamespace(server_port=port or 54321);runtime.mobile_origin=origin
        runtime.start_mobile=Mock(side_effect=start);runtime.stop_mobile=Mock()
        with patch('arise_app.mobile_setup.cli',side_effect=['{"BackendState":"Running","Self":{"DNSName":"pc.tail.ts.net."}}','{}','']) as command:
            result=prepare(runtime)
            self.assertTrue(result['ready']);self.assertEqual(command.call_args.args,('serve','--bg','http://127.0.0.1:54321'))
        runtime.mobile_server=None;resume(runtime)
        runtime.start_mobile.assert_called_with('https://pc.tail.ts.net',port=54321)
    def test_audio_format_rejected_before_loading_model(self):
        output=io.BytesIO()
        with wave.open(output,'wb') as f:f.setnchannels(2);f.setsampwidth(2);f.setframerate(16000);f.writeframes(b'\x00'*100)
        with self.assertRaises(ValueError):transcribe({},output.getvalue())

    def test_http_requires_totp_and_scopes_approvals(self):
        import http.client,json,threading
        from arise_app.companion import Devices,make_mobile_server
        chat=self.storage.create_conversation();other=self.storage.create_conversation()
        runtime=SimpleNamespace(storage=self.storage,devices=Devices(self.storage),mobile_security=self.security,
            conversation=chat,lock=threading.RLock(),transition_lock=threading.RLock(),approvals={},stop_generation=0,approve=Mock(),steer=Mock())
        secret=self.security.begin()['secret']
        with patch('arise_app.mobile_security.time.time',return_value=100000):self.security.confirm(otp(secret,100000//30))
        server=make_mobile_server(runtime,'https://pc.tail.ts.net');thread=threading.Thread(target=server.serve_forever);thread.start()
        def post(path,body,token=''):
            c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3)
            try:
                c.request('POST',path,json.dumps(body),{'Origin':'https://pc.tail.ts.net','Content-Type':'application/json','Cookie':'arise_device='+token})
                r=c.getresponse();status=r.status;cookie=r.getheader('Set-Cookie');r.read();return status,cookie
            finally:c.close()
        try:
            invite=runtime.devices.invite(chat)['code']
            with patch('arise_app.mobile_security.time.time',return_value=100030):
                self.assertEqual(post('/pair',{'code':invite,'name':'Phone'})[0],401)
                status,cookie=post('/pair',{'code':invite,'name':'Phone','otp':otp(secret,100030//30)})
                self.assertEqual(status,200);token=cookie.split(';')[0].split('=',1)[1]
                self.assertIn('HttpOnly',cookie);self.assertIn('Secure',cookie)
                self.assertEqual(post('/pair',{'code':invite,'name':'Phone','otp':otp(secret,100030//30)})[0],401)
                runtime.approvals['foreign']={'chat':other,'generation':0,'event':threading.Event()}
                self.assertEqual(post('/approval',{'id':'foreign','approved':False},token)[0],400)
                runtime.approve.assert_not_called()
                self.assertEqual(post('/api/config',{'code_enabled':True},token)[0],404)
                self.assertEqual(post('/logout',{},token)[0],200)
                self.assertEqual(post('/prompt',{'text':'hello'},token)[0],401)
        finally:server.shutdown();server.server_close();thread.join()
