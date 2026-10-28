import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock
from arise_app.assistant import Assistant


class TerminalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.r=Assistant(self.temp.name)
    def tearDown(self):
        self.r.close();self.r.storage.db.close();self.temp.cleanup()
    def test_denied_execution_and_changed_chat_never_spawn(self):
        r=self.r
        with patch('arise_app.terminal_tasks.sys.platform','win32'),patch('arise_app.terminal_tasks.subprocess.Popen') as spawn:
            with self.assertRaisesRegex(RuntimeError,'Autoriza'):r.terminals.delegate('Crear documento')
            r.storage.config.update(code_enabled=True,gentle_agent_home=self.temp.name)
            with patch.object(r,'ask_approval',side_effect=lambda *a:setattr(r,'stop_generation',r.stop_generation+1)):
                with self.assertRaisesRegex(RuntimeError,'cancelada'):r.terminals.delegate('Crear documento')
            spawn.assert_not_called()
    def test_launch_uses_gentle_and_separate_session_without_bridge_token(self):
        r=self.r;root=Path(self.temp.name)
        r.storage.config.update(code_enabled=True,gentle_agent_home=str(root/'home'),gentle_path=str(root/'gentle'),pi_command=['node',str(root/'cli.js')])
        process=Mock();process.poll.return_value=None
        with patch('arise_app.terminal_tasks.sys.platform','win32'),patch('arise_app.terminal_tasks.subprocess.CREATE_NEW_CONSOLE',16,create=True),patch('arise_app.terminal_tasks.subprocess.Popen',return_value=process) as spawn,patch.object(r,'ask_approval') as approval,patch.object(r.terminals,'watch'),patch.dict(os.environ,{'ARISE_TOKEN':'secret-parent','ARISE_URL':'parent-bridge'}):
            result=r.terminals.delegate('Tarea con espacios & caracteres')
            approval.assert_called_once()
            args=spawn.call_args.args[0];env=spawn.call_args.kwargs['env']
            self.assertIn('gentle-shell.mjs',args[1]);self.assertNotIn('Tarea con espacios & caracteres',args)
            self.assertNotIn('ARISE_TOKEN',env);self.assertNotIn('ARISE_URL',env)
            self.assertEqual(spawn.call_args.kwargs['creationflags'],16)
            self.assertIn(result['id'],args[args.index('--session')+1])
            self.assertEqual(json.loads((Path(env['ARISE_TERMINAL_TASK'])/'task.json').read_text())['task'],'Tarea con espacios & caracteres')
        process.poll.return_value=0

    def test_real_owned_process_stops_and_foreign_chat_cannot_cancel(self):
        r=self.r;identity='owned';directory=r.terminals.folder(r.conversation)/identity;directory.mkdir(parents=True)
        process=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'],start_new_session=os.name!='nt')
        job=dict(id=identity,chat=r.conversation,status='running',task='fixture',result='',error='',process=process)
        r.terminals.jobs[identity]=job;r.terminals.save(job)
        try:
            with self.assertRaises(ValueError):r.terminals.cancel(identity,'different-chat')
            self.assertIsNone(process.poll())
            r.stop()
            self.assertIsNotNone(process.poll())
            self.assertEqual(r.terminals.list(r.conversation)[0]['status'],'cancelled')
        finally:
            if process.poll() is None:process.kill();process.wait()
    def test_completion_is_saved_only_in_origin_chat_and_restart_never_replays(self):
        r=self.r;chat=r.conversation;identity='result';directory=r.terminals.folder(chat)/identity;directory.mkdir(parents=True)
        (directory/'result.json').write_text(json.dumps({'status':'completed','text':'Documento creado'}))
        job=dict(id=identity,chat=chat,status='running',task='fixture',result='',error='',process=Mock(wait=Mock(return_value=0),poll=Mock(return_value=0)))
        r.terminals.jobs[identity]=job;r.terminals.save(job)
        r.switch_conversation()
        r.terminals.watch(job)
        self.assertEqual(r.terminals.list(r.conversation),[])
        self.assertIn('Documento creado',str(r.storage.messages(chat)))
        self.assertNotIn('Documento creado',str(r.storage.messages(r.conversation)))
        job['status']='running';r.terminals.save(job);r.terminals.jobs.clear()
        self.assertEqual(r.terminals.list(chat)[0]['status'],'interrupted')
    def test_nonzero_exit_does_not_report_success(self):
        r=self.r;chat=r.conversation;identity='failed-exit'
        directory=r.terminals.folder(chat)/identity;directory.mkdir(parents=True)
        (directory/'result.json').write_text(json.dumps({'status':'completed','text':'Resultado parcial'}))
        job=dict(id=identity,chat=chat,status='running',task='fixture',result='',error='',process=Mock(wait=Mock(return_value=1),poll=Mock(return_value=1)))
        r.terminals.watch(job)
        self.assertEqual(job['status'],'failed')
        self.assertIn('Resultado parcial',job['result'])
        self.assertIn('código 1',job['error'])

    def completion_job(self):
        r=self.r; identity='notify-result'
        directory=r.terminals.folder(r.conversation)/identity;directory.mkdir(parents=True)
        (directory/'result.json').write_text(json.dumps({'status':'completed','text':'Documento creado'}))
        return dict(id=identity,chat=r.conversation,status='running',task='fixture',result='',error='',
                    epoch=r.pi_epoch,generation=r.stop_generation,
                    process=Mock(wait=Mock(return_value=0),poll=Mock(return_value=0)))

    def test_idle_completion_wakes_parent_once_and_records_result(self):
        r=self.r;r.storage.config['code_enabled']=True
        job=self.completion_job();parent=Mock();parent.request.return_value={'data':{'disposition':'started'}}
        r.pi=parent
        try:
            r.terminals.watch(job);r.terminals.watch(job)
            parent.request.assert_called_once()
            payload=parent.request.call_args.args[0]
            self.assertEqual(payload['type'],'prompt');self.assertEqual(payload['streamingBehavior'],'followUp')
            self.assertTrue(r.busy);self.assertFalse(r.settled.is_set())
            self.assertEqual(len([m for m in r.storage.messages(r.conversation) if 'Documento creado' in str(m)]),1)
            r.pi_event({'type':'message_end','message':{'role':'assistant','content':[{'type':'text','text':'Resultado verificado'}]}})
            r.pi_event({'type':'agent_settled'})
            self.assertFalse(r.busy)
        finally:r.pi=None

    def test_completion_does_not_replace_active_task_or_restore_permissions(self):
        r=self.r;job=self.completion_job();parent=Mock();r.pi=parent
        try:
            for field,value in [('generation',-1),('epoch',-1),('chat','another-chat')]:
                r.storage.config['code_enabled']=True
                self.assertFalse(r.deliver_terminal_completion({**job,field:value}))
            r.storage.config['code_enabled']=False
            self.assertFalse(r.deliver_terminal_completion(job));parent.request.assert_not_called()
            r.storage.config['code_enabled']=True;r.busy=True;r.current_task='existing'
            self.assertTrue(r.deliver_terminal_completion(job))
            self.assertEqual(r.current_task,'existing');self.assertFalse(r.desktop)
        finally:r.pi=None;r.current_task=None;r.busy=False

    def test_completion_rpc_failure_visible_and_not_retried(self):
        r=self.r;r.storage.config['code_enabled']=True;job=self.completion_job()
        parent=Mock();parent.request.side_effect=TimeoutError();r.pi=parent
        try:
            with patch.object(r,'emit') as emit:
                r.terminals.watch(job);r.terminals.watch(job)
                self.assertTrue(any(c.args[0]=='error' for c in emit.call_args_list))
            parent.request.assert_called_once();self.assertFalse(r.busy)
            self.assertIn('Documento creado',str(r.storage.messages(r.conversation)))
        finally:r.pi=None

    def test_extension_submits_once_excludes_thinking_and_closes(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'task.json').write_text(json.dumps({'task':'Tarea explícita'}))
            extension=(Path(__file__).resolve().parents[1]/'arise_app/resources/terminal-task.mjs').as_uri()
            script='''import extension from EXTENSION;
import {readFileSync} from 'node:fs';import {join} from 'node:path';
const hooks={},sent=[];let closed=0;
extension({on:(name,fn)=>hooks[name]=fn,sendUserMessage:t=>sent.push(t)});
const ctx={ui:{notify(){}},shutdown(){closed++}};
hooks.session_start({},ctx);hooks.session_start({},ctx);
if(sent.length!==1)throw Error('duplicated task');
if(!hooks.tool_call({toolName:'orchestrator_send_message'}).block)throw Error('peer leak');
hooks.agent_end({messages:[{role:'assistant',content:[{type:'thinking',thinking:'PRIVATE'},{type:'text',text:'public result'}]}]},ctx);
const result=JSON.parse(readFileSync(join(process.env.ARISE_TERMINAL_TASK,'result.json'),'utf8'));
if(result.text!=='public result'||closed!==1)throw Error('bad result');
console.log(result.status);
'''.replace('EXTENSION',json.dumps(extension))
            p=subprocess.run(['node','--input-type=module','-e',script],env={**os.environ,'ARISE_TERMINAL_TASK':temp},capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(p.stdout.strip(),'completed')
