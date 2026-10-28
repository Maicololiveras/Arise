"""User-approved Gentle terminals owned by one ARISE chat. No peer broadcasting."""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import uuid
import psutil

TOOLS = [
    {'name':'terminal.delegate','description':'Abre Gentle en una terminal Windows propia para una tarea del chat. Requiere ejecución local y confirmación visible; devuelve un ID, no un resultado terminado. No concede manos/ojos.','inputSchema':{'type':'object','properties':{'task':{'type':'string'}},'required':['task'],'additionalProperties':False}},
    {'name':'terminal.list','description':'Estado y resultados públicos de las terminales delegadas de este chat. No enumera otros chats ni terminales ajenas.','inputSchema':{'type':'object','properties':{}}},
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
        code=job['process'].wait()
        with self.lock:
            if job['status'] not in ('running','starting'):return
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
            self.save(job)
            # Results stay in the originating chat even after the user switches.
            with self.runtime.lock:
                self.runtime.storage.message(job['chat'],'assistant',f"Terminal {job['id'][:8]} · {job['status']}\n"+(job['result'] or job['error']))
                if self.runtime.conversation==job['chat']:
                    self.runtime.publish_activity({'type':'subagent_status','task_id':job['id'],'status':job['status']})
                    self.runtime.emit('notice',{'text':f"Terminal {job['id'][:8]}: {job['status']}. Consulta terminal.list para revisar el resultado."})
        # Do not hold terminal/runtime locks across an RPC acknowledgement.
        self.runtime.deliver_terminal_completion(job)


    def cancel(self, identity, chat):
        with self.lock:
            job=self.jobs.get(identity)
            if not job or job['chat']!=chat:raise ValueError('La terminal no pertenece a este chat activo.')
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
                if record['id'] not in self.jobs and record['status'] in ('running','starting'):
                    record.update(status='interrupted',error='ARISE reinició; no se reconecta ni reenvía automáticamente.')
                records.append(record)
            except (OSError,ValueError,KeyError):continue
        return records
