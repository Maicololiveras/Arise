"""User-approved Gentle terminals owned by one ARISE chat. No peer broadcasting."""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import uuid
import psutil

TOOLS = [
    {'name':'terminal.delegate','description':'Abre Gentle en una terminal Windows propia para una tarea del chat. Requiere ejecución local y confirmación visible; devuelve un ID, no un resultado terminado. No concede manos/ojos.','inputSchema':{'type':'object','properties':{'task':{'type':'string'}},'required':['task'],'additionalProperties':False}},
    {'name':'terminal.list','description':'Estado y resultados públicos de las terminales delegadas de este chat. No enumera otros chats ni terminales ajenas.','inputSchema':{'type':'object','properties':{}}},
    {'name':'terminal.send','description':'Envía una respuesta o nueva indicación a una terminal activa de este chat. No amplía permisos. La recepción no significa tarea terminada.','inputSchema':{'type':'object','properties':{'id':{'type':'string'},'text':{'type':'string','minLength':1,'maxLength':12000}},'required':['id','text'],'additionalProperties':False}},
    {'name':'terminal.cancel','description':'Detiene una terminal delegada propia y sus procesos hijos.','inputSchema':{'type':'object','properties':{'id':{'type':'string'}},'required':['id']}},
]


class TerminalTasks:
    def __init__(self, runtime):
        self.runtime=runtime
        self.lock=threading.RLock()
        self.jobs={}

    def folder(self, chat):
        return Path(self.runtime.sessions.get(chat)['folder'])/'terminals'

    def save(self, job):
        record={key:job[key] for key in ('id','chat','status','task','result','error')}
        path=self.folder(job['chat'])/job['id']/'record.json'
        temp=path.with_suffix('.tmp')
        temp.write_text(json.dumps(record,ensure_ascii=False),encoding='utf-8')
        temp.replace(path)

    def delegate(self, task):
        r=self.runtime
        if sys.platform!='win32': raise RuntimeError('Delegar en terminal está disponible en Windows; no se abrió ningún proceso.')
        if not isinstance(task,str) or not task.strip() or len(task)>12000: raise ValueError('La tarea debe tener entre 1 y 12.000 caracteres.')
        with r.transition_lock:
            chat=r.conversation; generation=r.stop_generation
            if not r.storage.config.get('code_enabled'): raise RuntimeError('Autoriza la ejecución local en este chat antes de delegar.')
            if not r.storage.config.get('gentle_agent_home'): raise RuntimeError('Configura y verifica el entorno oficial de Gentle antes de abrir una terminal delegada.')
        r.ask_approval('Delegar tarea en terminal',task+'\n\nCarpeta: '+r.storage.config['workspace']+'\nSe detendrá al cambiar de chat o pulsar Detener. No recibe el control de pantalla ni manos de ARISE.')
        with r.transition_lock, self.lock:
            if r.conversation!=chat or r.stop_generation!=generation or not r.storage.config.get('code_enabled'):
                raise RuntimeError('Delegación cancelada: cambió el chat, la autorización o se pulsó Detener.')
            config=r.storage.config
            command=config['pi_command']
            if len(command)!=2 or Path(command[0]).stem.lower()!='node': raise RuntimeError('Se necesita el Node y Pi directos de la instalación de Gentle.')
            if sum(j['process'].poll() is None for j in self.jobs.values())>=3: raise RuntimeError('Hay tres terminales activas. Detén o termina una antes de abrir otra.')
            identity=uuid.uuid4().hex
            directory=self.folder(chat)/identity; directory.mkdir(parents=True)
            (directory/'task.json').write_text(json.dumps({'task':task}),encoding='utf-8')
            resources=Path(__file__).parent/'resources'
            args=[command[0],str(resources/'gentle-shell.mjs'),command[1], '--extension',str(resources/'terminal-task.mjs'), '--session',str(directory/'session.jsonl')]
            if config.get('agent_provider') and config.get('agent_model'):args+=['--provider',config['agent_provider'],'--model',config['agent_model']]
            if config.get('thinking'):args+=['--thinking',config['thinking']]
            env={k:v for k,v in os.environ.items() if not k.startswith('ARISE_')}
            env.update(r.credentials.environment())
            env.update(ARISE_TERMINAL_TASK=str(directory),ARISE_GENTLE_ROOT=config['gentle_path'],ARISE_GENTLE_HOME=config['gentle_agent_home'],PI_CODING_AGENT_DIR=config['gentle_agent_home'])
            if config.get('gentle_bundle_root'):env['ARISE_GENTLE_PREFIX']=config['gentle_bundle_root']
            job=dict(id=identity,chat=chat,status='starting',task=task,result='',error='',epoch=r.pi_epoch,generation=generation)
            try:
                process=subprocess.Popen(args,cwd=config['workspace'],env=env,creationflags=subprocess.CREATE_NEW_CONSOLE)
            except Exception:
                job.update(status='failed',error='No se pudo abrir la terminal.');self.save(job);raise
            job.update(process=process,status='running');self.jobs[identity]=job;self.save(job)
            r.publish_activity({'type':'subagent_status','task_id':identity,'status':'running'})
            threading.Thread(target=self.watch,args=(job,),daemon=True).start()
            return {key:job[key] for key in ('id','chat','status')}

    def watch(self, job):
        while job['process'].poll() is None:
            self.receive(job)
            time.sleep(.2)
        code=job['process'].wait()
        with self.lock:
            if job['status'] not in ('running','starting','waiting','waiting_user'):return
            path=self.folder(job['chat'])/job['id']/'result.json'
            try:
                if path.stat().st_size>200000: raise ValueError()
                report=json.loads(path.read_text(encoding='utf-8'))
                if report.get('status') not in ('completed','failed'):raise ValueError()
                job.update(status=report['status'],result=str(report.get('text',''))[:60000],error='' if report['status']=='completed' else 'Gentle informó un fallo.')
                if code != 0:
                    job.update(status='failed',error=f'Gentle dejó un resultado parcial pero cerró con código {code}. Verifica antes de repetir.')
            except (OSError,ValueError):
                job.update(status='failed',error=f'Terminal cerrada sin resultado confirmado (salida {code}). Revisa los archivos antes de repetir.')
            self.clear_dialogs(job['id'])
            self.save(job)
            # Results stay in the originating chat even after the user switches.
            with self.runtime.lock:
                self.runtime.storage.message(job['chat'],'assistant',f"Terminal {job['id'][:8]} · {job['status']}\n"+(job['result'] or job['error']))
                if self.runtime.conversation==job['chat']:
                    self.runtime.publish_activity({'type':'subagent_status','task_id':job['id'],'status':job['status']})
                    self.runtime.emit('notice',{'text':f"Terminal {job['id'][:8]}: {job['status']}. Consulta terminal.list para revisar el resultado."})
        # Do not hold terminal/runtime locks across an RPC acknowledgement.
        self.runtime.deliver_terminal_completion(job)


    def _owned_active(self, identity, chat):
        job = self.jobs.get(identity)
        r = self.runtime
        if (not job or job['chat'] != chat or chat != r.conversation
                or job.get('generation') != r.stop_generation or job.get('epoch') != r.pi_epoch
                or not r.storage.config.get('code_enabled') or job['process'].poll() is not None):
            raise ValueError('La terminal ya no está activa o no pertenece a este chat autorizado.')
        return job

    def send(self, identity, text, chat):
        if not isinstance(text,str) or not text.strip() or len(text)>12000:
            raise ValueError('La indicación debe tener entre 1 y 12.000 caracteres.')
        with self.runtime.transition_lock, self.lock:
            job=self._owned_active(identity,chat)
            directory=self.folder(chat)/identity
            if job.get('question'):
                self.reply(identity,job['question'],{'value':text},chat)
                return {'id':identity,'status':'reply_sent'}
            inbox=directory/'inbox';inbox.mkdir(exist_ok=True)
            if len(list(inbox.glob('*.json')))>=32:raise RuntimeError('La terminal tiene demasiadas indicaciones pendientes.')
            job['message_sequence']=job.get('message_sequence',0)+1
            target=inbox/(f"{job['message_sequence']:020d}-"+uuid.uuid4().hex+'.json');tmp=target.with_suffix('.tmp')
            tmp.write_text(json.dumps({'text':text}),encoding='utf-8');tmp.replace(target)
            return {'id':identity,'status':'queued','message_id':target.stem}

    def reply(self, identity, request_id, data, chat):
        with self.runtime.transition_lock, self.lock:
            job=self._owned_active(identity,chat)
            if job.get('question')!=request_id:raise ValueError('La pregunta ya no está pendiente.')
            value=data.get('value','')
            if not isinstance(value,str) or len(value)>12000:raise ValueError('Respuesta demasiado larga.')
            target=self.folder(chat)/identity/('reply-'+request_id+'.json')
            tmp=target.with_suffix('.tmp');tmp.write_text(json.dumps({'value':value,'cancelled':bool(data.get('cancelled'))}),encoding='utf-8');tmp.replace(target)
            job.pop('question',None)
            dialog_id='terminal:'+identity+':'+request_id
            self.runtime.dialogs.pop(dialog_id,None)
            self.runtime.emit('dialog_resolved',{'id':dialog_id})
            return {'sent':True}

    def receive(self, job):
        r=self.runtime
        try:
            path=self.folder(job['chat'])/job['id']/'state.json'
            if path.stat().st_size>300000:return
            raw=path.read_text(encoding='utf-8')
            if job.get('last_state')==raw:return
            state=json.loads(raw)
            if state.get('status') not in ('running','waiting','waiting_user'):return
            with r.transition_lock, self.lock:
                self._owned_active(job['id'],job['chat'])
                job['last_state']=raw;job['status']=state['status']
                text=str(state.get('text',''))[:60000]
                if text:
                    job['result']=text
                    r.storage.message(job['chat'],'assistant',f"Terminal {job['id'][:8]} · pendiente\n"+text)
                    r.emit('notice',{'text':f"Terminal {job['id'][:8]} espera indicaciones. Puedes responder en este chat."})
                request=state.get('question')
                if isinstance(request,dict):
                    request_id=request.get('id','');prompt=request.get('prompt')
                    try:valid_id=str(uuid.UUID(request_id))==request_id
                    except (ValueError,TypeError,AttributeError):valid_id=False
                    if valid_id and isinstance(prompt,str) and 0<len(prompt)<=12000:
                        job['question']=request_id
                        dialog_id='terminal:'+job['id']+':'+request_id
                        record={'id':dialog_id,'method':'input','title':'Pregunta de terminal '+job['id'][:8],
                                'message':prompt,'terminal_id':job['id'],'request_id':request_id,'chat':job['chat']}
                        r.dialogs[dialog_id]=record
                        r.storage.message(job['chat'],'assistant',f"Terminal {job['id'][:8]} pregunta:\n"+prompt)
                        r.emit('dialog',record)
                self.save(job)
                r.publish_activity({'type':'subagent_status','task_id':job['id'],'status':job['status']})
            if state['status']=='waiting':
                r.deliver_terminal_completion(job)
        except (OSError,ValueError,TypeError):return

    def clear_dialogs(self, identity):
        for dialog_id, record in list(self.runtime.dialogs.items()):
            if record.get('terminal_id')==identity:
                self.runtime.dialogs.pop(dialog_id,None)
                self.runtime.emit('dialog_resolved',{'id':dialog_id})

    def cancel(self, identity, chat):
        with self.lock:
            job=self.jobs.get(identity)
            if not job or job['chat']!=chat:raise ValueError('La terminal no pertenece a este chat activo.')
            self.clear_dialogs(identity)
            process=job['process']
            if process.poll() is not None:return {'id':identity,'status':job['status']}
            if os.name != 'nt':
                import signal
                try: os.killpg(process.pid,signal.SIGTERM)
                except ProcessLookupError: pass
                try: process.wait(timeout=2)
                except subprocess.TimeoutExpired: pass
                try: os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError: pass
                process.wait(timeout=2)
            else:
                try: children=psutil.Process(process.pid).children(recursive=True)
                except psutil.NoSuchProcess: children=[]
                process.terminate()
                for child in children:
                    try:child.terminate()
                    except psutil.NoSuchProcess:pass
                _,alive=psutil.wait_procs(children,timeout=2)
                for child in alive:
                    try:child.kill()
                    except psutil.NoSuchProcess:pass
                _,alive=psutil.wait_procs(alive,timeout=2)
                try:process.wait(timeout=2)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=2)
                if alive:raise RuntimeError('No se pudo confirmar la parada de todos los procesos de la terminal.')
            job.update(status='cancelled',error='Detenida por ARISE; revisa posibles resultados parciales.');self.save(job)
            if self.runtime.conversation==job['chat']:
                self.runtime.publish_activity({'type':'subagent_status','task_id':identity,'status':'cancelled'})
            return {'id':identity,'status':'cancelled'}

    def stop_all(self):
        with self.lock:
            for job in list(self.jobs.values()):
                if job['process'].poll() is None:self.cancel(job['id'],job['chat'])

    def list(self, chat):
        records=[]
        for path in sorted(self.folder(chat).glob('*/record.json'))[-100:]:
            try:
                if path.stat().st_size>200000:continue
                record=json.loads(path.read_text(encoding='utf-8'))
                if record.get('chat')!=chat:continue
                if record['id'] not in self.jobs and record['status'] in ('running','starting','waiting','waiting_user'):
                    record.update(status='interrupted',error='ARISE reinició; no se reconecta ni reenvía automáticamente.')
                records.append(record)
            except (OSError,ValueError,KeyError):continue
        return records
