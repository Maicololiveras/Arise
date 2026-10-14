"""Real Pi/Gentle RPC and child processes; deterministic local model, no cloud credentials."""
import json
import os
import shutil
import tempfile
import threading
import select
import psutil
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from docx import Document
from arise_app.assistant import Assistant
from arise_app.server import make_server
from test_pi_real import CLI

def peer_disconnected(connection):
    try:
        return connection.recv(1) == b''
    except ConnectionResetError:
        # Windows reports a force-closed socket as WSAECONNRESET (10054).
        return True

class SocketClosureTests(unittest.TestCase):
    def test_eof_and_reset_confirm_close_but_timeout_does_not(self):
        from unittest.mock import Mock
        self.assertTrue(peer_disconnected(Mock(recv=Mock(return_value=b''))))
        self.assertTrue(peer_disconnected(Mock(recv=Mock(side_effect=ConnectionResetError(10054,'reset')))))
        self.assertFalse(peer_disconnected(Mock(recv=Mock(return_value=b'x'))))
        with self.assertRaises(TimeoutError):
            peer_disconnected(Mock(recv=Mock(side_effect=TimeoutError('still open'))))

@unittest.skipUnless(CLI.is_file() and shutil.which('node'), 'Pi real requerido')
class OrchestratorRealTests(unittest.TestCase):
    def test_docx_local_tools_subagent_same_chat_switch_return(self):
        requests=[]; results=[]; child_started=threading.Event(); release_child=threading.Event(); child_disconnected=threading.Event()
        class Model(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_POST(self):
                body=json.loads(self.rfile.read(int(self.headers['Content-Length']))); requests.append(body)
                messages=body['messages']; last=max(i for i,m in enumerate(messages) if m['role']=='user')
                content=messages[last]['content']; instruction=content if isinstance(content,str) else '\n'.join(b.get('text','') for b in content); after=messages[last+1:]
                system=str([m['content'] for m in messages if m['role']=='system'])
                delta={'role':'assistant'}; finish='stop'
                if 'TEST_CHILD_SYSTEM' in system:
                    if 'WAIT_BACKGROUND' in instruction:
                        child_started.set()
                        while not release_child.is_set():
                            if select.select([self.connection],[],[],.1)[0]:
                                if peer_disconnected(self.connection):
                                    child_disconnected.set();return
                    delta['content']='CHILD_VERIFIED'
                elif any(m['role']=='tool' for m in after):
                    results.extend(m['content'] for m in after if m['role']=='tool')
                    delta['content']='Resultado comprobado de la herramienta.'
                else:
                    if instruction=='documento':
                        name='arise_call'; args={'name':'documents.create_docx','arguments_json':json.dumps({'path':'report.docx','title':'QA Word','paragraphs':['Contenido real desde Pi y Gentle.']})}
                    elif instruction in ('delegar','background'):
                        name='subagent_run'; args={'agent':'probe','task':'WAIT_BACKGROUND' if instruction=='background' else 'Responde a la prueba.','mode':'background' if instruction=='background' else 'task'}
                    elif instruction=='escribir':
                        name='write'; args={'path':'authorized.txt','content':'authorized local task'}
                    else:
                        delta['content']='Segunda respuesta'; name=None
                    if name:
                        delta['tool_calls']=[{'index':0,'id':'call-'+str(len(requests)),'type':'function','function':{'name':name,'arguments':json.dumps(args)}}]; finish='tool_calls'
                self.send_response(200); self.send_header('Content-Type','text/event-stream'); self.end_headers()
                for d,f in ((delta,None),({},finish)):
                    self.wfile.write(('data: '+json.dumps({'id':'fixture','object':'chat.completion.chunk','choices':[{'index':0,'delta':d,'finish_reason':f}]})+'\n\n').encode());self.wfile.flush()
                self.wfile.write(b'data: [DONE]\n\n')
        model=ThreadingHTTPServer(('127.0.0.1',0),Model);threading.Thread(target=model.serve_forever,daemon=True).start()
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);home=root/'agent';home.mkdir(); work=root/'workspace';work.mkdir()
            (home/'settings.json').write_text(json.dumps({'telemetry':False,'packages':[]}))
            (home/'models.json').write_text(json.dumps({'providers':{'arise-test':{'baseUrl':f'http://127.0.0.1:{model.server_port}/v1','api':'openai-completions','apiKey':'fixture-only','models':[{'id':'arise-test','input':['text'],'reasoning':False,'contextWindow':32000,'maxTokens':4000}]}}}))
            definitions=work/'.pi'/'agents';definitions.mkdir(parents=True)
            (definitions/'probe.md').write_text('---\nname: probe\ndescription: QA read-only probe\ntools: read\nmodel: arise-test/arise-test\nthinking: off\n---\nTEST_CHILD_SYSTEM. Responde con el resultado de la prueba.\n')
            r=Assistant(root/'data');r.select_project(str(work))
            r.storage.config.update(pi_command=[shutil.which('node'),str(CLI)],pi_extra_args=['--offline','--no-extensions','--no-skills','--no-context-files'],agent_provider='arise-test',agent_model='arise-test',thinking='off',gentle_path=str(CLI.parents[4]/'gentle-pi'),mcp={})
            bridge=make_server(r);threading.Thread(target=bridge.serve_forever,daemon=True).start()
            env={'PI_CODING_AGENT_DIR':str(home),'PI_OFFLINE':'1','PI_TELEMETRY':'0','GENTLE_PI_CONFIG_HOME':str(root/'gentle-config')}
            def prompt(text):
                task=r.prompt(text)['task_id'];self.assertTrue(r.settled.wait(35),text)
                self.assertEqual(r.tasks[task]['status'],'done',r.tasks[task])
            try:
                with patch.dict(os.environ,env):
                    prompt('documento');process=r.pi.process;session=r.pi_state['sessionId'];chat=r.conversation
                    self.assertTrue((work/'report.docx').exists(),str(requests)[-5000:]+str(results));self.assertEqual(Document(work/'report.docx').paragraphs[-1].text,'Contenido real desde Pi y Gentle.')
                    prompt('segundo');self.assertIs(r.pi.process,process)
                    self.assertEqual(r.pi_state['sessionId'],session)
                    self.assertTrue(r.capabilities()['gentle_verified'])
                    self.assertIn('subagent_run',r.capabilities()['pi_tools_observed'])
                    prompt('delegar')
                    self.assertFalse(any('TEST_CHILD_SYSTEM' in str(b['messages']) for b in requests))
                    self.assertIn('no autorizada',str(results))
                    r.settings({'code_enabled':True})
                    prompt('escribir');self.assertEqual((work/'authorized.txt').read_text(),'authorized local task')
                    prompt('delegar')
                    self.assertTrue(any('TEST_CHILD_SYSTEM' in str(b['messages']) for b in requests),str(results)[-4000:])
                    self.assertIn('CHILD_VERIFIED',str(results))
                    self.assertTrue(any(e['kind']=='activity' and any('Subagente' in line for line in e['data']['details']) for e in r.events))
                    self.assertEqual(r.pi_state['sessionId'],session)
                    process=r.pi.process;other=r.switch_conversation()['id']
                    self.assertIsNotNone(process.poll());self.assertFalse(r.storage.config['code_enabled'])
                    prompt('segundo');self.assertNotEqual(r.pi_state['sessionId'],session)
                    r.switch_conversation(chat);r.connect_pi();self.assertEqual(r.pi_state['sessionId'],session)
                    self.assertTrue(r.storage.config['code_enabled']);self.assertFalse(r.desktop)
                    self.assertNotIn('QA Word',str(r.storage.messages(other)))
                    prompt('background');self.assertTrue(child_started.wait(10))
                    parent=r.pi.process;self.assertIsNone(parent.poll(),str(list(r.events)[-10:]))
                    children=psutil.Process(parent.pid).children(recursive=True) if os.name=='nt' else []
                    if os.name=='nt':self.assertTrue(children,"No se observó el proceso del subagente Windows")
                    r.stop()
                    self.assertTrue(child_disconnected.wait(10),"El subagente no canceló su petición al modelo")
                    release_child.set()
                    self.assertIsNone(r.pi);self.assertIsNotNone(parent.poll())
                    for child in children:
                        self.assertFalse(child.is_running(),f"El proceso hijo {child.pid} sobrevivió a la parada")
                    self.assertTrue(r.desktop_halted)
                    self.assertEqual(r.activity.snapshot()['phase'],'stopped')
            finally:
                release_child.set()
                r.close();r.storage.db.close();bridge.shutdown();bridge.server_close()
        model.shutdown();model.server_close()
