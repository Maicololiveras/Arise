"""Prove the study tool guard runs inside real Pi, including built-in shell calls."""
import json
import os
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from unittest.mock import patch
from arise_app.assistant import Assistant
from arise_app.server import make_server
from test_pi_real import CLI

class StudyPiTests(unittest.TestCase):
    def test_read_only_turn_blocks_builtin_and_bridge_tools(self):
        seen=[]
        class Model(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                results=[m for m in body['messages'] if m.get('role')=='tool']
                seen[:] = results
                if len(results)<2:
                    name,args = ('bash',{'command':'echo study-must-not-run'}) if not results else ('arise_call',{'name':'memory.save','arguments_json':'{"text":"must not save"}'})
                    delta={'role':'assistant','tool_calls':[{'index':0,'id':'blocked-'+str(len(results)),'type':'function','function':{'name':name,'arguments':json.dumps(args)}}]};finish='tool_calls'
                else:delta={'role':'assistant','content':'Study explanation.'};finish='stop'
                self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
                for d,f in ((delta,None),({},finish)):
                    self.wfile.write(('data: '+json.dumps({'id':'fixture','object':'chat.completion.chunk','choices':[{'index':0,'delta':d,'finish_reason':f}]})+'\n\n').encode());self.wfile.flush()
                self.wfile.write(b'data: [DONE]\n\n')
        server=ThreadingHTTPServer(('127.0.0.1',0),Model);threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory);home=root/'agent';home.mkdir()
                (home/'settings.json').write_text('{"packages":[],"telemetry":false}')
                (home/'models.json').write_text(json.dumps({'providers':{'fixture':{'baseUrl':f'http://127.0.0.1:{server.server_port}/v1','api':'openai-completions','apiKey':'fixture','models':[{'id':'fixture','input':['text'],'reasoning':False,'contextWindow':32000,'maxTokens':2000}]}}}))
                r=Assistant(root/'arise');r.storage.config.update(pi_command=[shutil.which('node'),str(CLI)],pi_extra_args=['--offline','--no-extensions','--no-skills','--no-context-files'],gentle_path=str(CLI.parents[4]/'gentle-pi'),agent_provider='fixture',agent_model='fixture',thinking='off',code_enabled=True)
                bridge=make_server(r);threading.Thread(target=bridge.serve_forever,daemon=True).start()
                try:
                    with patch.dict(os.environ,{'PI_CODING_AGENT_DIR':str(home),'PI_OFFLINE':'1','GENTLE_PI_CONFIG_HOME':str(root/'gentle')}):
                        r.connect_pi();r.study.guarded=True;r.prompt('Explain this question without tools.')
                    self.assertTrue(r.settled.wait(20))
                    self.assertEqual(len(seen),2)
                    for response in seen:self.assertIn('Study turns only analyze',str(response))
                    self.assertFalse(r.memory_path.exists())
                finally:r.close();r.storage.db.close();bridge.shutdown();bridge.server_close()
        finally:server.shutdown();server.server_close()
