import json,threading,unittest,tempfile
from collections import deque
from unittest.mock import Mock
from arise_app.storage import Storage
from arise_app.runtime import Runtime
from arise_app.desktop_probe import DesktopProbe, SCHEMA

class DesktopRecoveryTests(unittest.TestCase):
    def test_pages_do_not_shift_or_mix_chats(self):
        with tempfile.TemporaryDirectory() as root:
            s=Storage(root)
            try:
                for i in range(61):
                    s.message('alpha','user',str(i))
                    s.message('alpha','system','hidden')
                    s.message('beta','user','other')
                latest=s.message_page('alpha')
                s.message('alpha','user','new')
                older=s.message_page('alpha',latest['before'])
                self.assertIsNone(older['before'])
                self.assertEqual([m['text'] for m in older['messages']+latest['messages']],[str(i) for i in range(61)])
            finally:s.db.close()

    def test_lost_cursor_and_active_questions(self):
        rt=Runtime.__new__(Runtime);rt.lock=rt.transition_lock=threading.RLock()
        rt.sequence=99;rt.events=deque([{'seq':98},{'seq':99}])
        self.assertTrue(rt.events_after(22)['gap']);self.assertTrue(rt.events_after(100)['gap'])
        self.assertFalse(rt.events_after(97)['gap'])
        rt.storage=Mock();rt.conversation='a';rt.current_message='partial';rt.busy=True;rt.dialogs={}
        rt.approvals={k:dict(chat=k,action='check',preview='',event=threading.Event()) for k in ('a','b')}
        snap=rt.desktop_snapshot();self.assertEqual(snap['cursor'],99);self.assertEqual(snap['partial'],'partial')
        self.assertEqual([p['id'] for p in snap['approvals']],['a'])
        rt.busy=False;self.assertEqual(rt.desktop_snapshot()['partial'],'')

    def test_discovery_reads_only_advertised_fields(self):
        p=DesktopProbe(Mock());p.request('capabilities')
        def reply(method,data):
            key=next(k for k,v in p.pending.items() if v==method)
            p.widget({'widgetLines':[json.dumps(dict(schema=SCHEMA,kind='response',requestId=key,ok=True,data=data))]})
        reply('capabilities',{'methods':['get_permission_mode','get_config','list_jobs','set_config']})
        self.assertNotIn('set_config',p.pending.values())
        reply('get_permission_mode',{'mode':'normal'});reply('get_config',{'store':'profiles','status':'ok','value':{'active':'team'}})
        reply('list_jobs',{'jobs':[{},{}]})
        self.assertEqual((p.state['permission'],p.state['profile'],p.state['jobs']),('normal','team',2))
