import json
import os
from pathlib import Path
import shutil
import tempfile
import threading
import time
import unittest
import urllib.request
import urllib.error
from unittest.mock import patch
from arise_app.assistant import Assistant
from arise_app.server import make_server
from arise_app.processes import JsonProcess

ROOT=Path(__file__).resolve().parents[1]

class AccountsTests(unittest.TestCase):
    def setup_runtime(self,t):
        r=Assistant(Path(t)/'data');home=Path(t)/'agent';home.mkdir();modules=ROOT/'vendor/node_modules'
        r.settings({'pi_command':[shutil.which('node'),str(modules/'@earendil-works/pi-coding-agent/dist/bundle/cli.js')],
                    'gentle_agent_home':str(home),'gentle_path':str(modules/'gentle-pi')})
        return r,home

    def wait_state(self,r,owner,state):
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            value=r.accounts.call('status',{'owner':owner})
            if value['state']==state:return value
            if value['state']=='error':self.fail(str(value))
            time.sleep(.05)
        self.fail('Account state timed out: '+str(value))

    def test_real_sdk_api_key_store_models_logout_and_no_secret_events(self):
        with tempfile.TemporaryDirectory() as t:
            r,home=self.setup_runtime(t);owner='window-owner-0000000';secret='sk-arise-local-fixture-NOT-REAL'
            try:
                result=r.accounts.call('providers',{'owner':owner})
                self.assertIn('openai',[p['id'] for p in result['providers']])
                anthropic=next(p for p in result['providers'] if p['id']=='anthropic')
                self.assertEqual(anthropic['methods'],['api_key'])
                r.accounts.call('start',{'owner':owner,'provider':'openai','method':'api_key'})
                prompt=self.wait_state(r,owner,'prompt')['prompt']
                with self.assertRaises(RuntimeError):r.connect_pi()
                with self.assertRaises(RuntimeError):r.settings({'thinking':'high'})
                with self.assertRaises(RuntimeError):r.accounts.call('answer',{'owner':'other-window-000000','prompt_id':prompt['id'],'value':secret})
                r.accounts.call('answer',{'owner':owner,'prompt_id':prompt['id'],'value':secret})
                self.wait_state(r,owner,'done')
                self.assertIn(secret,(home/'auth.json').read_text())
                models=r.accounts.call('models',{'owner':owner,'provider':'openai'})['models']
                self.assertTrue(models)
                model=models[0]
                r.accounts.call('select_model',{'owner':owner,'provider':'openai','model':model['id']})
                self.assertEqual(r.storage.config['agent_model'],model['id'])
                r.accounts.call('logout',{'owner':owner,'provider':'openai'})
                self.assertNotIn(secret,(home/'auth.json').read_text())
                self.assertNotIn(secret,json.dumps(list(r.events)))
                self.assertNotIn(secret,r.storage.config_path.read_text())
            finally:r.close();r.storage.db.close()

    def test_agent_token_cannot_access_accounts(self):
        with tempfile.TemporaryDirectory() as t:
            r,home=self.setup_runtime(t);server=make_server(r);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                request=urllib.request.Request(r.url+'/api/accounts/providers',data=b'{"owner":"window-owner-0000000"}',headers={'Authorization':'Bearer '+r.token,'Content-Type':'application/json'})
                with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(request)
                self.assertEqual(error.exception.code,403)
                self.assertIsNone(r.accounts.process)
                ack=urllib.request.Request(r.url+'/api/desktop/layout-ack',data=b'{"id":"fake"}',headers={'Authorization':'Bearer '+r.token,'Content-Type':'application/json'})
                with self.assertRaises(urllib.error.HTTPError) as denied:urllib.request.urlopen(ack)
                self.assertEqual(denied.exception.code,403)
                request.add_header('X-Arise-Accounts',r.accounts_token)
                with urllib.request.urlopen(request,timeout=30) as response:self.assertTrue(json.load(response)['providers'])
            finally:r.close();r.storage.db.close();server.shutdown();server.server_close();thread.join(5)

    def test_cancel_releases_helper_and_stale_window_cannot_reply(self):
        with tempfile.TemporaryDirectory() as t:
            r,home=self.setup_runtime(t);owner='window-owner-0000000'
            try:
                r.accounts.call('providers',{'owner':owner})
                r.accounts.call('start',{'owner':owner,'provider':'openai','method':'api_key'})
                prompt=self.wait_state(r,owner,'prompt');process=r.accounts.process.process
                r.accounts.call('cancel',{'owner':owner})
                self.assertIsNotNone(process.poll());self.assertFalse(r.accounts.active)
                self.assertFalse((home/'auth.json').exists() and 'sk-' in (home/'auth.json').read_text())
                with self.assertRaises(RuntimeError):r.accounts.call('answer',{'owner':owner,'prompt_id':prompt['prompt']['id'],'value':'stale'})
            finally:r.close();r.storage.db.close()

    def test_oauth_bridge_prompts_select_codes_and_sanitizes_failures(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'dist').mkdir();(root/'package.json').write_text('{"type":"module"}')
            (root/'dist/index.js').write_text('''
export class SettingsManager {static create(){return {getOrCreateDeviceId:()=>"fixture"};}}
export class ModelRuntime {
 static async create(){return new ModelRuntime();}
 getProviders(){return [{id:'fixture',name:'Fixture',auth:{oauth:{name:'Fixture OAuth'}}}];}
 getProviderAuthStatus(){return {configured:false};}
 async login(p,m,i){
  i.notify({type:'device_code',userCode:'ABCD',verificationUri:'https://example.com/device'});
  const region=await i.prompt({type:'select',message:'Region',options:[{id:'eu',label:'Europe'}]});
  const code=await i.prompt({type:'manual_code',message:'Code'});
  if(region!=='eu'||code!=='ok')throw Error('SECRET-SERVER-DETAIL');
 }
}
''')
            env={**os.environ,'ARISE_AUTH_PACKAGE':str(root),'PI_CODING_AGENT_DIR':str(root)};env.pop('ARISE_GENTLE_ROOT',None)
            process=JsonProcess([shutil.which('node'),str(ROOT/'arise_app/resources/provider-auth.mjs')],cwd=root,env=env)
            try:
                result=process.request({'action':'start','provider':'fixture','method':'oauth'})['data']
                for _ in range(50):
                    result=process.request({'action':'status'})['data']
                    if result.get('prompt'):break
                    time.sleep(.02)
                self.assertEqual(result['notice']['code'],'ABCD');self.assertEqual(result['prompt']['kind'],'select')
                process.request({'action':'answer','prompt_id':result['prompt']['id'],'value':'eu'})
                for _ in range(50):
                    result=process.request({'action':'status'})['data']
                    if result.get('prompt',{}).get('kind')=='manual_code':break
                    time.sleep(.02)
                process.request({'action':'answer','prompt_id':result['prompt']['id'],'value':'bad'})
                for _ in range(50):
                    result=process.request({'action':'status'})['data']
                    if result['state']=='error':break
                    time.sleep(.02)
                self.assertEqual(result['state'],'error');self.assertNotIn('SECRET',json.dumps(result))
            finally:process.close()
