import http.client,json,sys,tempfile,threading,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from arise_app.processes import JsonProcess
from arise_app.desktop_feed import receive
from arise_app.runtime import Runtime
from arise_app.server import make_server

class ChannelTests(unittest.TestCase):
    def test_slow_event_consumer_does_not_hold_rpc_response(self):
        release=threading.Event();entered=threading.Event()
        def event(record):
            if record.get('type')=='agent_start':
                entered.set();release.wait(4)
        proc=JsonProcess([sys.executable,str(Path(__file__).with_name('fake_agent.py'))],on_event=event)
        try:
            proc.request({'type':'prompt','message':'wait'})
            self.assertTrue(entered.wait(2))
            self.assertTrue(proc.request({'type':'get_state'},timeout=1)['success'])
        finally:release.set();proc.close()

    def test_known_session_plain_prompt_needs_one_rpc(self):
        proc=Mock();proc.request.return_value={'data':{'disposition':'started'}}
        rt=SimpleNamespace(storage=SimpleNamespace(config={}),last_prompt_language='es',pi_epoch=3,
                           pi_state={'sessionFile':'existing'},current_task='t')
        Runtime._submit_prompt(rt,'hola','t',proc,3,False)
        proc.request.assert_called_once_with({'type':'prompt','message':'hola'},timeout=30)

    def test_authenticated_reusable_socket_and_resume(self):
        with tempfile.TemporaryDirectory() as root:
            rt=Runtime(root);server=make_server(rt)
            server_thread=threading.Thread(target=server.serve_forever,daemon=True);server_thread.start()
            conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=4)
            headers={'Authorization':'Bearer '+rt.token,'X-Arise-Accounts':rt.accounts_token}
            try:
                conn.request('GET','/api/desktop/events?after=0',headers={'Authorization':headers['Authorization']})
                resp=conn.getresponse();self.assertEqual(resp.status,403);resp.read()
                rt.emit('one',{});conn.request('GET','/api/desktop/events?after=0',headers=headers)
                resp=conn.getresponse();self.assertEqual(json.load(resp)['cursor'],1);sock=conn.sock;self.assertIsNotNone(sock)
                conn.request('GET','/api/desktop/events?after=1',headers=headers);rt.emit('two',{})
                self.assertEqual(json.load(conn.getresponse())['events'][0]['kind'],'two');self.assertIs(conn.sock,sock)
                got=[];stop=threading.Event()
                def callback(batch):
                    got.extend(e['kind'] for e in batch['events']);stop.set();return True
                receive(rt,1,stop,callback,lambda:self.fail('unexpected disconnect'))
                self.assertEqual(got,['two'])
            finally:
                conn.close();server.shutdown();server.server_close();rt.close();rt.storage.db.close()
