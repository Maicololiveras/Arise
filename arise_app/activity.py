"""Public, content-free activity projection. Never consume thought or tool-result text."""
import re
from collections import deque

PHASES = {'waiting':'Esperando', 'running':'En curso · fase no informada', 'exploring':'Explorando',
          'executing':'Ejecutando', 'verifying':'Verificando', 'done':'Finalizado', 'error':'Error', 'stopped':'Detenido'}

def identifier(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_.:/@+-]{1,96}', value): return ''
    if re.search(r'^(sk-|gh[pousr]_|github_pat_)|token|secret|password', value, re.I): return ''
    return value

class PublicActivity:
    def __init__(self):
        self.phase='waiting'; self.tool=''; self.model=''; self.model_source=''
        self.completed=set(); self.children={}; self.lines=deque(maxlen=30)
        self.parent_running=False; self.halted=False
    def snapshot(self):
        active=sum(s in ('queued','running','waiting') for s in self.children.values())
        return {'phase': self.phase, 'label': PHASES[self.phase], 'tool': self.tool,
                'model': self.model, 'model_source': self.model_source,
                'tools_completed':len(self.completed), 'subagents_active':active,
                'progress_total':None, 'details':list(self.lines)}
    def model_state(self, model, source='selected'):
        if not isinstance(model,dict): return
        value=identifier(model.get('id') or model.get('model'))
        provider=identifier(model.get('provider'))
        self.model=(provider+'/' if provider else '')+value if value else ''
        self.model_source=source if self.model else ''
    def consume(self, event):
        kind=event.get('type')
        if kind=='run_start':
            self.completed.clear();self.lines.clear();self.halted=False;self.parent_running=True
            self.phase='running';self.tool='';self.lines.append('Solicitud aceptada por ARISE.');return True
        if kind=='stop':
            self.halted=True;self.parent_running=False;self.phase='stopped';self.tool='';self.children.clear()
            self.lines.append('Parada solicitada; no se reanudan acciones automáticamente.');return True
        if self.halted: return False
        if kind=='message_start':
            message=event.get('message',{})
            if message.get('role')!='assistant': return False
            self.model_state(message,'response');return True
        if kind=='tool_execution_start':
            name=identifier(event.get('toolName')) or 'Herramienta sin nombre informado'
            args=event.get('args',{})
            if name=='arise_call' and isinstance(args,dict): name=identifier(args.get('name')) or name
            self.tool=name
            self.phase='exploring' if name in ('read','ls','find','grep','files.list','files.read') else 'verifying' if name=='documents.read_docx' else 'executing'
            self.lines.append('Inicio: '+name);return True
        if kind=='tool_execution_end':
            name=identifier(event.get('toolName')) or 'Herramienta'
            identity=identifier(event.get('toolCallId'))
            if identity:self.completed.add(identity)
            self.lines.append(('Falló: ' if event.get('isError') else 'Terminó: ')+name)
            self.phase='error' if event.get('isError') else 'running';self.tool='';return True
        if kind=='subagent_status':
            identity=identifier(event.get('task_id'));status=event.get('status')
            if not identity or status not in ('queued','running','waiting','completed','failed','cancelled','timed_out'):return False
            if self.children.get(identity)==status:return False
            self.children[identity]=status
            labels={'queued':'en cola','running':'ejecutando','waiting':'esperando','completed':'finalizado','failed':'falló','cancelled':'cancelado','timed_out':'tiempo agotado'}
            self.lines.append('Subagente '+identity[:8]+': '+labels[status])
            active=any(s in ('queued','running','waiting') for s in self.children.values())
            self.phase='executing' if active else 'running' if self.parent_running else 'done'
            if status in ('failed','timed_out'):self.phase='error'
            elif status=='waiting':self.phase='waiting'
            return True
        if kind=='document_verified':
            count=event.get('paragraphs')
            if type(count) is not int or not 1 <= count <= 1000:return False
            self.lines.append(f'Resultado: Word creado y contenido verificado ({count} párrafos añadidos).')
            return True
        if kind=='waiting':
            self.phase='waiting';self.lines.append('Esperando una respuesta o confirmación del usuario.');return True
        if kind in ('finished','process_closed'):
            self.parent_running=False;self.tool=''
            self.phase='error' if event.get('error') or kind=='process_closed' else 'executing' if any(s in ('queued','running','waiting') for s in self.children.values()) else 'done'
            self.lines.append('La ejecución terminó con un error; revisa el aviso del chat.' if self.phase=='error' else 'El agente principal terminó su turno.')
            return True
        # Deliberately ignore message_update (including thinking_delta), prompts,
        # command arguments, result bodies, exception details and arbitrary text.
        return False
