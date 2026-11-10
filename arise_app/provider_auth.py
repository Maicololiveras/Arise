"""Private desktop account sessions, isolated from the agent's tool bridge."""
import json
import os
from pathlib import Path
import threading
from .processes import JsonProcess


class ProviderAccounts:
    def __init__(self, runtime):
        self.runtime=runtime
        self.lock=threading.RLock()
        self.process=None
        self.owner=None
        self.timer=None
        self.active=False
        self.chat=None

    def _idle(self):
        r=self.runtime
        if r.busy or r.pi_has_children or any(j['process'].poll() is None for j in getattr(getattr(r,'terminals',None),'jobs',{}).values()):
            raise RuntimeError('Detén las tareas antes de cambiar las cuentas del agente.')

    def _open(self, owner):
        if not isinstance(owner,str) or not 16<=len(owner)<=100:raise ValueError('Sesión de ajustes inválida.')
        if self.process:
            if self.owner!=owner:raise RuntimeError('Hay otra ventana de cuentas abierta. Ciérrala primero.')
            return
        self._idle()
        r=self.runtime
        from .memory_selection import validate
        validate(r.storage.config)
        from .bundle import configure_bundle
        configure_bundle(r)
        c=r.storage.config
        if not c.get('gentle_agent_home'):raise RuntimeError('Configura el motor integrado antes de conectar tu cuenta.')
        command=c['pi_command']
        if len(command)!=2:raise RuntimeError('Configura el Node y Pi directos del motor integrado.')
        package=None
        for parent in Path(command[1]).resolve().parents:
            meta=parent/'package.json'
            if meta.is_file():
                try:
                    if json.loads(meta.read_text()).get('name')=='@earendil-works/pi-coding-agent':package=parent;break
                except (ValueError,OSError):pass
        if not package:raise RuntimeError('No se encontró la API de cuentas del motor. Repara ARISE.')
        from .memory_selection import validate
        validate(c)
        from .owned_engine import environment
        env=environment({**os.environ,**r.credentials.environment()},c)
        for key in list(env):
            if key.startswith('ARISE_'):env.pop(key)
        env.update(ARISE_AUTH_PACKAGE=str(package),PI_CODING_AGENT_DIR=c['gentle_agent_home'],ARISE_GENTLE_ROOT=c.get('gentle_path',''))
        self.process=JsonProcess([command[0],'--use-system-ca',str(Path(__file__).parent/'resources/provider-auth.mjs')],cwd=c['workspace'],env=env)
        self.owner=owner;self.chat=r.conversation
        self.timer=threading.Timer(600,self.close);self.timer.daemon=True;self.timer.start()

    def call(self, action, data):
        with self.runtime.transition_lock,self.lock:
            owner=data.get('owner')
            if action=='close':
                if self.owner==owner:self.close()
                return {'closed':True}
            if action not in {'providers','models','start','status','answer','cancel','logout','select_model'}:raise ValueError('Operación de cuenta inválida.')
            if action=='providers':self._open(owner)
            if not self.process or self.owner!=owner:raise RuntimeError('La ventana de cuentas caducó. Vuelve a abrirla.')
            if self.chat!=self.runtime.conversation:
                self.close();raise RuntimeError('El chat cambió. Vuelve a abrir Cuentas.')
            if action in {'start','logout','select_model'}:
                self._idle()
                if self.active:raise RuntimeError('Termina o cancela el acceso actual.')
                self.runtime.disconnect_pi()
            if action=='select_model':
                result=self.process.request({'action':'models','provider':data.get('provider')})['data']
                if not any(m['id']==data.get('model') and m['provider']==data.get('provider') for m in result['models']):raise ValueError('Modelo no disponible.')
                self.runtime.settings({'agent_provider':data['provider'],'agent_model':data['model']})
                return {'selected':True}
            if action=='start':self.active=True
            allowed={k:data[k] for k in ('provider','method','prompt_id','value') if k in data}
            try:
                result=self.process.request({'action':action,**allowed},timeout=30)['data']
                if result.get('state') in {'done','error','cancelled'}:self.active=False
                if action=='cancel':
                    # Terminating the helper also releases provider callback sockets promptly.
                    self.close()
                return result
            except Exception:
                self.close()
                raise RuntimeError('No se pudo completar la operación de cuenta. Cierra esta ventana y vuelve a intentarlo.') from None

    def close(self):
        with self.lock:
            if self.timer:self.timer.cancel();self.timer=None
            process=self.process;self.process=None;self.owner=None;self.active=False;self.chat=None
            if process:process.close()
