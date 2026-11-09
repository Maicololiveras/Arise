import copy
from datetime import datetime, timezone
import http.client
import json
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from arise_app.storage import Storage
from arise_app.connections import Connections, ConnectionError
from arise_app.companion import Devices, make_mobile_server
from arise_app.reminders import Reminders


class MemoryVault:
    def __init__(self): self.value={}
    def read(self): return copy.deepcopy(self.value)
    def write(self,value): self.value=copy.deepcopy(value)


class ConnectionTests(unittest.TestCase):
    def setUp(self):
        self.request=Mock(return_value={'ok':True})
        self.vault=MemoryVault()
        self.c=Connections('.',request=self.request,vault=self.vault)

    def test_telegram_send_and_status_never_exposes_token(self):
        self.c.save_token('telegram','123456:example-token')
        self.c.send('telegram','123','Hola')
        self.assertEqual(self.request.call_args.args[1],{'chat_id':'123','text':'Hola'})
        self.assertNotIn('example-token',json.dumps(self.c.status()))
        self.assertFalse(self.c.status()[0]['verified'])

    def test_disconnect_prevents_delivery(self):
        self.c.save_token('telegram','123456:example-token');self.c.disconnect('telegram')
        with self.assertRaises(ConnectionError):self.c.send('telegram','123','Hola')
        self.request.assert_not_called()

    def test_whatsapp_uses_explicit_template(self):
        self.c.save_token('whatsapp','example-token',phone_id='123',api_version='v24.0',template='recordatorio',language='es_CO')
        self.c.send('whatsapp','573001234567','Hola')
        body=self.request.call_args.args[1]
        self.assertEqual(body['type'],'template');self.assertEqual(body['template']['name'],'recordatorio')

    def test_invalid_whatsapp_configuration_rejected(self):
        with self.assertRaises(ValueError):self.c.save_token('whatsapp','example-token',phone_id='../',api_version='latest')

    def test_oauth_pending_slowdown_and_refresh(self):
        self.request.return_value={'device_code':'private','user_code':'ABCD','verification_uri':'https://microsoft.com/devicelogin','expires_in':900,'interval':5}
        result=self.c.oauth_start('teams','11111111-1111-1111-1111-111111111111')
        self.assertNotIn('device_code',result)
        self.assertEqual(self.c.oauth_poll('teams'),{'status':'pending'})
        self.c.pending['teams']['next_poll']=0
        self.request.return_value={'error':'slow_down'};self.c.oauth_poll('teams')
        self.assertEqual(self.c.pending['teams']['interval'],10)
        self.c.pending['teams']['next_poll']=0
        self.request.return_value={'access_token':'first','refresh_token':'refresh','expires_in':1}
        self.assertEqual(self.c.oauth_poll('teams')['status'],'connected')
        self.request.return_value={'access_token':'fresh','expires_in':3600}
        self.c.send('teams','19:chat@thread.v2','Hola')
        self.assertEqual(self.request.call_args.kwargs['token'],'fresh')


class DurableTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.s=Storage(self.temp.name)
        self.chat=self.s.create_conversation();self.other=self.s.create_conversation()
        self.r=SimpleNamespace(storage=self.s,conversation=self.chat,stop_generation=0,
            transition_lock=threading.RLock(),lock=threading.RLock(),approvals={},connections=SimpleNamespace(providers=Connections.providers,send=Mock()),
            ask_approval=Mock(),emit=Mock(),steer=Mock(return_value={'task_id':'task'}),stop=Mock())
        self.r.devices=Devices(self.s);self.jobs=Reminders(self.r)
    def tearDown(self):self.jobs.close();self.s.db.close();self.temp.cleanup()
    def args(self,**kwargs):return {'text':'Revisar informe','at':datetime.fromtimestamp(time.time()+60,timezone.utc).isoformat(),**kwargs}

    def test_chat_fallback_persistent_once_across_restart(self):
        self.jobs.create(self.chat,self.args());self.r.conversation=self.other
        self.jobs.tick(time.time()+70);Reminders(self.r).tick(time.time()+70)
        self.assertEqual(len(self.s.messages(self.chat)),1);self.assertEqual(self.s.messages(self.other),[])
        self.r.emit.assert_not_called();self.r.connections.send.assert_not_called()

    def test_ambiguous_send_not_replayed(self):
        self.r.connections.send.side_effect=TimeoutError()
        self.jobs.create(self.chat,self.args(provider='telegram',destination='123'))
        self.jobs.tick(time.time()+70);self.jobs.tick(time.time()+80)
        self.assertEqual(self.r.connections.send.call_count,1)
        self.assertEqual(len(self.s.messages(self.chat)),2)

    def test_crash_in_delivery_is_reported_without_retry(self):
        with self.s.db:self.s.db.execute('INSERT INTO reminder_deliveries VALUES(?,?,?,?)',('x','j',self.chat,'sending'))
        Reminders(self.r);Reminders(self.r)
        self.assertEqual(len(self.s.messages(self.chat)),1)
        self.r.connections.send.assert_not_called()

    def test_cancel_scoped_and_recurrence_coalesces(self):
        job=self.jobs.create(self.chat,self.args(every_seconds=60))
        with self.assertRaises(ValueError):self.jobs.cancel(self.other,job['id'])
        self.jobs.tick(time.time()+3600)
        self.assertEqual(len(self.s.messages(self.chat)),1)
        self.jobs.cancel(self.chat,job['id']);self.jobs.tick(time.time()+7200)
        self.assertEqual(len(self.s.messages(self.chat)),1)

    def test_approval_change_chat_or_stop_aborts_creation(self):
        self.r.ask_approval.side_effect=lambda *a:setattr(self.r,'stop_generation',1)
        with self.assertRaises(ValueError):self.jobs.create(self.chat,self.args())
        self.assertEqual(self.jobs.list(self.chat),[])

    def test_naive_datetime_rejected(self):
        with self.assertRaises(ValueError):self.jobs.create(self.chat,self.args(at='2099-01-01T09:00:00'))

    def test_pair_one_use_rotation_and_revocation(self):
        code=self.r.devices.invite(self.chat)['code'];token=self.r.devices.pair(code,'Mi celular')
        with self.assertRaises(ValueError):self.r.devices.pair(code,'Otro')
        device=self.r.devices.authorize(token)
        new=self.r.devices.rotate(token)
        with self.assertRaises(PermissionError):self.r.devices.authorize(token)
        self.assertEqual(self.r.devices.authorize(new)['chat'],self.chat)
        self.r.devices.revoke(self.other,device['id']);self.r.devices.authorize(new)
        self.r.devices.revoke(self.chat,device['id'])
        with self.assertRaises(PermissionError):self.r.devices.authorize(new)
        self.assertNotIn(new,json.dumps(self.r.devices.list(self.chat)))

    def test_expired_pair_and_session_rejected(self):
        invite=self.r.devices.invite(self.chat)
        with patch('arise_app.companion.time.time',return_value=time.time()+301):
            with self.assertRaises(ValueError):self.r.devices.pair(invite['code'],'phone')
        token=self.r.devices.pair(invite['code'],'phone')
        with patch('arise_app.companion.time.time',return_value=time.time()+901):
            with self.assertRaises(PermissionError):self.r.devices.rotate(token)

    def test_mobile_http_authorization_chat_and_privilege_boundaries(self):
        server=make_mobile_server(self.r,'https://pc.example.ts.net')
        thread=threading.Thread(target=server.serve_forever);thread.start()
        token=self.r.devices.pair(self.r.devices.invite(self.chat)['code'],'phone')
        def post(path,body,origin='https://pc.example.ts.net'):
            client=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3)
            try:
                client.request('POST',path,json.dumps(body),{'Content-Type':'application/json','Origin':origin,'Cookie':'arise_device='+token})
                response=client.getresponse();status=response.status;response.read();return status
            finally:client.close()
        try:
            self.assertEqual(post('/prompt',{'text':'Hola'},'https://evil.example'),403)
            self.assertEqual(post('/api/config',{'code_enabled':True}),404)
            self.assertEqual(post('/prompt',{'text':'Hola'}),200)
            self.assertEqual(self.r.steer.call_count,1)
            self.r.conversation=self.other
            self.assertEqual(post('/prompt',{'text':'Otro'}),409)
            self.assertEqual(post('/stop',{}),409)
            self.r.stop.assert_not_called()
        finally:server.shutdown();server.server_close();thread.join()


if __name__=='__main__':unittest.main()
