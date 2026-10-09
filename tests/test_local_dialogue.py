import io
import json
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from arise_app.assistant import Assistant
from arise_app.local_dialogue import LocalDialogue
from arise_app.local_voice import LocalVoiceBridge
from test_local_live import wait_for

class DialogueTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.runtime=Assistant(self.temp.name)
        self.requests=[]
        owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):self.reply({'data':[{'id':'fixture-local-model'}]})
            def do_POST(self):
                body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));owner.requests.append(body);last=body['messages'][-1]
                if last['role']=='tool':message={'role':'assistant','content':'Estoy en ello.'}
                elif 'Resultado confirmado' in last['content']:message={'role':'assistant','content':'Gentle terminó: resultado real.'}
                elif last['content']=='haz tarea':message={'role':'assistant','content':None,'tool_calls':[{'id':'delegate-1','type':'function','function':{'name':'delegate_task','arguments':json.dumps({'instruction':'trabaja en la carpeta elegida'})}}]}
                else:message={'role':'assistant','content':'Podemos conversar mientras Gentle trabaja.'}
                self.reply({'choices':[{'message':message}]})
            def reply(self,data):
                raw=json.dumps(data).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.runtime.storage.config.update({'local_dialogue_enabled':True,'local_dialogue_url':f'http://127.0.0.1:{self.server.server_port}/v1','local_dialogue_model':''})
    def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join();self.runtime.close();self.runtime.storage.db.close();self.temp.cleanup()
    def test_model_tools_acknowledge_delegation_and_keep_turn_pairs_on_restart(self):
        dialogue=LocalDialogue(self.runtime);calls=[]
        reply=dialogue.respond('haz tarea',lambda name,args:calls.append((name,args)) or {'status':'accepted'})
        self.assertEqual(reply,'Estoy en ello.');self.assertEqual(calls[0][0],'delegate_task')
        second=LocalDialogue(self.runtime);self.assertEqual(second.model,'fixture-local-model')
        self.assertTrue(any(m.get('tool_calls') for m in second.history));self.assertTrue(any(m['role']=='tool' for m in second.history))
        self.assertEqual(second.respond('hablemos',lambda *a:None),'Podemos conversar mientras Gentle trabaja.')
        self.assertTrue(any(m.get('content')=='haz tarea' for m in self.requests[-1]['messages']))
    def test_interlocutor_talks_while_gentle_runs_and_reports_confirmed_result(self):
        active=threading.Event();active.set();shutdown=threading.Event();spoken=[];instructions=[]
        def steer(text):instructions.append(text);self.runtime.tasks['real-task']={'status':'running','output':'','error':''};return {'task_id':'real-task'}
        self.runtime.steer=steer
        bridge=LocalVoiceBridge(self.runtime,SimpleNamespace(interrupt=lambda:None),lambda text,cancel:spoken.append(text),active,shutdown)
        try:
            bridge.submit('haz tarea');wait_for(lambda:'Estoy en ello.' in spoken)
            wait_for(lambda:bool(instructions));self.assertEqual(instructions,['trabaja en la carpeta elegida'])
            bridge.submit('hablemos');wait_for(lambda:'Podemos conversar mientras Gentle trabaja.' in spoken)
            self.assertEqual(self.runtime.tasks['real-task']['status'],'running')
            self.runtime.tasks['real-task'].update(status='completed',output='resultado real')
            wait_for(lambda:'Gentle terminó: resultado real.' in spoken)
            self.assertEqual(self.requests[-1]['tool_choice'],'none')
            self.assertEqual(len(instructions),1)
        finally:bridge.close()
    def test_external_endpoint_is_rejected_and_results_cannot_invoke_tools(self):
        self.runtime.storage.config['local_dialogue_url']='https://external.example/v1'
        with self.assertRaises(ValueError):LocalDialogue(self.runtime)
        self.runtime.storage.config['local_dialogue_url']=f'http://127.0.0.1:{self.server.server_port}/v1'
        dialogue=LocalDialogue(self.runtime)
        call={'choices':[{'message':{'content':'','tool_calls':[{'id':'bad','function':{'name':'delegate_task','arguments':'{}'}}]}}]}
        dialogue.request=lambda *a,**kw:call;calls=[]
        with self.assertRaises(ValueError):dialogue.respond('resultado confirmado',lambda *a:calls.append(a),result=True)
        self.assertEqual(calls,[])
    def test_history_is_bounded_without_orphaning_tool_results(self):
        for index in range(12):self.runtime.storage.save_voice_turn(self.runtime.conversation,[{'role':'user','content':str(index)},{'role':'assistant','content':'x'*4000}])
        history=self.runtime.storage.voice_history(self.runtime.conversation)
        self.assertLessEqual(len(json.dumps(history)),21000)
        self.assertEqual(history[0]['role'],'user');self.assertEqual(history[-1]['content'],'x'*4000)
