import http.cookiejar
import json
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from arise_app.gateway import make_gateway

class Remote:
    def __init__(self):self.called=[]
    def events_after(self,cursor):return {'events':[],'cursor':cursor}
    def request(self,path):return {'messages':[]}
    def steer(self,text):self.called.append(text);return {'task_id':'one'}
    def status(self):return {'version':'0.2.0'}
    def stop(self):return {'stopped':True}

class GatewayTests(unittest.TestCase):
    def test_authentication_csrf_and_remote_prompt(self):
        remote=Remote();origin='http://127.0.0.1:0';password='test-only-strong-password'
        server=make_gateway(remote,password,origin,0);threading.Thread(target=server.serve_forever,daemon=True).start()
        url=f'http://127.0.0.1:{server.server_port}'
        jar=http.cookiejar.CookieJar();opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        def request(path,data=None,csrf=None):
            headers={'Host':'127.0.0.1:0','Origin':origin}
            if csrf:headers['X-CSRF']=csrf
            raw=None if data is None else json.dumps(data).encode()
            return opener.open(urllib.request.Request(url+path,data=raw,headers=headers))
        try:
            with self.assertRaises(urllib.error.HTTPError) as error:request('/api/status')
            self.assertEqual(error.exception.code,401)
            login=urllib.request.Request(url+'/login',data=urllib.parse.urlencode({'password':password}).encode(),headers={'Host':'127.0.0.1:0','Origin':origin})
            with opener.open(login) as response:self.assertEqual(response.status,200)
            with request('/api/session') as response:csrf=json.load(response)['csrf']
            with self.assertRaises(urllib.error.HTTPError) as error:request('/api/prompt',{'text':'blocked'})
            self.assertEqual(error.exception.code,403)
            with request('/api/prompt',{'text':'Tarea remota'},csrf) as response:self.assertEqual(json.load(response)['task_id'],'one')
            self.assertEqual(remote.called,['Tarea remota'])
        finally:server.shutdown();server.server_close()
    def test_rejects_non_https_public_access(self):
        with self.assertRaises(ValueError):make_gateway(Remote(),'test-only-strong-password','http://public.example',0)
