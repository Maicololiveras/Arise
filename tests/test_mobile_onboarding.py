from pathlib import Path
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
    def test_old_host_serve_configuration_never_restarts(self):
        runtime = SimpleNamespace(storage=self.storage, mobile_security=self.security)
        save_settings(runtime, {'enabled':True,'origin':'https://old.tail.ts.net','port':54321})
        with patch('arise_app.mobile_setup.TailNode') as launch:
            resume(runtime)
            launch.assert_not_called()

    def test_enrollment_and_resume_use_private_node(self):
        import threading
        runtime = SimpleNamespace(storage=self.storage, mobile_security=Mock(enabled=lambda: True),
                                  mobile_lock=threading.RLock(), mobile_server=None)
        node = Mock(origin='https://arise-mobile.tail.ts.net')
        node.process.poll.return_value = None
        with patch('arise_app.mobile_setup.binary',return_value=Path(__file__)), patch('arise_app.mobile_setup.TailNode',return_value=node) as launch:
            with self.assertRaises(ValueError): prepare(runtime)
            prepare(runtime,'one-use-test')
            launch.assert_called_once_with(runtime,'one-use-test')
            prepare(runtime)
            self.assertEqual(launch.call_count,1)
            self.assertNotIn('one-use-test',next(self.storage.root.glob('mobile-*-v1-server.json')).read_text())
            runtime.mobile_server = None
            resume(runtime)
            launch.assert_called_with(runtime,'')

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
                c.request('POST',runtime.devices.channel.api+path,json.dumps(body),{'Origin':'https://pc.tail.ts.net','Content-Type':'application/json','Cookie':runtime.devices.channel.cookie+'='+token})
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
                def get_agents():
                    c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3)
                    try:
                        c.request('GET',runtime.devices.channel.api+'/agents',headers={'Cookie':runtime.devices.channel.cookie+'='+token})
                        return json.loads(c.getresponse().read())
                    finally: c.close()
                runtime.pi=Mock()
                runtime.pi.process.poll.return_value=None
                runtime.shell_control=Mock(return_value={'supported':True,'data':{'agents':[{'agent':'planner','id':'a','status':'running','lastStep':'writing','prompt':'private fixture'}]}})
                self.assertEqual(get_agents()['agents'],[{'agent':'planner','id':'a','status':'running','lastStep':'writing'}])
                runtime.conversation=other
                self.assertEqual(get_agents()['agents'],[])
                runtime.shell_control.assert_called_once_with(chat,'list_subagents',{})
                runtime.conversation=chat
                runtime.approvals['foreign']={'chat':other,'generation':0,'event':threading.Event()}
                self.assertEqual(post('/approval',{'id':'foreign','approved':False},token)[0],400)
                runtime.approve.assert_not_called()
                self.assertEqual(post('/api/config',{'code_enabled':True},token)[0],404)
                self.assertEqual(post('/logout',{},token)[0],200)
                self.assertEqual(post('/prompt',{'text':'hello'},token)[0],401)
        finally:server.shutdown();server.server_close();thread.join()

class ReadinessTests(unittest.TestCase):
    def test_readiness_never_changes_network_or_enrollment(self):
        from arise_app.mobile_setup import readiness
        r=SimpleNamespace(mobile_security=Mock(enabled=Mock(return_value=True)),mobile_server=Mock())
        r.mobile_server.process.poll.return_value=None
        with patch('arise_app.mobile_setup.binary',return_value=Path(__file__)):
            value=readiness(r)
        self.assertTrue(value['ready_to_pair'])
        self.assertFalse(value['steps'][-1]['ready'])
        r.mobile_security.begin.assert_not_called()

class MobileChannelTests(unittest.TestCase):
    def test_same_storage_and_peer_do_not_share_any_channel_credential(self):
        from arise_app.mobile_channel import MobileChannel
        from arise_app.companion import Devices
        with tempfile.TemporaryDirectory() as root:
            storage = Storage(root)
            self.addCleanup(storage.db.close)
            chat = storage.create_conversation()
            preview, stable = [Devices(storage, ch) for ch in MobileChannel]
            invitations = [svc.invite(chat)['code'] for svc in (preview,stable)]
            with self.assertRaises(ValueError): stable.pair(invitations[0],'phone',peer='same')
            with self.assertRaises(ValueError): preview.pair(invitations[1],'phone',peer='same')
            tokens = [svc.pair(code,'phone',peer='same') for svc,code in zip((preview,stable),invitations)]
            for own, other, token in ((preview,stable,tokens[0]), (stable,preview,tokens[1])):
                self.assertNotEqual(own.channel.api,other.channel.api)
                self.assertNotEqual(own.channel.cookie,other.channel.cookie)
                with self.assertRaises(PermissionError): other.rotate(token,'same')
                other.revoke(chat,own.authorize(token,'same')['id'])
                self.assertEqual(own.authorize(token,'same')['chat'],chat)
            a,b = [MobileSecurity(storage, channel=ch) for ch in MobileChannel]
            self.assertNotEqual(a.vault.path,b.vault.path)
            a.vault,b.vault = Vault(),Vault()
            asecret,bsecret = a.begin()['secret'], b.begin()['secret']
            self.assertNotEqual(asecret,bsecret)
            with patch('arise_app.mobile_security.time.time', return_value=123456789):
                step=123456789//30
                a.confirm(otp(asecret,step))
                b.confirm(otp(bsecret,step))
                for _ in range(5):
                    with self.assertRaises(PermissionError): a.verify('invalid')
            with patch('arise_app.mobile_security.time.time',return_value=123456819):
                b.verify(otp(bsecret,step+1))
