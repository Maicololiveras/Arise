"""Concurrent speech bridge. Pi/Gentle owns reasoning, tasks and session context."""
import queue
import threading
import unicodedata

def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFD',text.lower().strip(' .,!¿?¡')) if unicodedata.category(c) != 'Mn')

class LocalVoiceBridge:
    def __init__(self, runtime, audio, say, active, shutdown):
        self.runtime, self.audio, self.say, self.active, self.shutdown = runtime, audio, say, active, shutdown
        self.conversation = runtime.conversation
        self.closed = threading.Event(); self.lock = threading.RLock()
        self.generation = 0; self.cancel_speech = threading.Event(); self.interrupted = False
        self.commands = queue.Queue(maxsize=8); self.responses = queue.Queue(maxsize=8)
        self.asked = set()
        self.threads = [threading.Thread(target=self._commands,daemon=True,name='arise-local-delegate'),threading.Thread(target=self._responses,daemon=True,name='arise-local-speech')]
        for thread in self.threads: thread.start()
    def valid(self):
        return not self.closed.is_set() and self.active.is_set() and not self.shutdown.is_set() and self.runtime.conversation == self.conversation
    def interrupt(self):
        with self.lock:
            self.generation += 1; self.cancel_speech.set(); self.interrupted = True
        self.audio.interrupt()
    def submit(self, text):
        if not self.valid() or not text.strip(): return
        self.interrupt()
        try: self.commands.put_nowait((text,self.generation))
        except queue.Full: self.runtime.emit('notice',{'text':'Hay demasiadas instrucciones de voz pendientes; espera un momento.'})
    def speak(self,text,epoch=None):
        try: self.responses.put_nowait((text,self.generation if epoch is None else epoch))
        except queue.Full: pass
    def _commands(self):
        while not self.closed.is_set():
            try: text,epoch = self.commands.get(timeout=.1)
            except queue.Empty: continue
            if not self.valid(): continue
            try:
                clean = normalize(text)
                self.runtime.emit('voice_transcript',{'role':'user','text':text})
                if clean in ('deja de hablar','silencio','para de hablar'): continue
                if clean in ('cancela la tarea','detente','cancelar'):
                    self.runtime.stop(); continue
                if self.answer_question(text): continue
                task = self.runtime.steer(text)
                threading.Thread(target=self._wait_result,args=(task['task_id'],epoch),daemon=True,name='arise-local-result').start()
            except Exception as error: self.runtime.emit('error',{'text':str(error)[:300]})
    def _wait_result(self, identity, epoch):
        while self.valid() and epoch == self.generation:
            result = self.runtime.tasks.get(identity)
            if result and result['status'] != 'running':
                reply=result.get('error') or result.get('output')
                if reply: self.speak(reply,epoch)
                return
            self.closed.wait(.05)
    def _responses(self):
        while not self.closed.is_set():
            try: text,epoch=self.responses.get(timeout=.1)
            except queue.Empty: continue
            with self.lock:
                if not self.valid() or epoch != self.generation: continue
                cancel=threading.Event(); self.cancel_speech=cancel
            self.runtime.emit('voice_transcript',{'role':'assistant','text':text})
            try: self.say(text,cancel)
            except Exception as error: self.runtime.emit('error',{'text':str(error)[:300]})
    def poll_questions(self):
        if not self.valid(): return
        for identity,question in list(self.runtime.dialogs.items()):
            if identity in self.asked: continue
            self.asked.add(identity)
            options=question.get('options',[])
            suffix=' '.join(f'Opción {i+1}: {value}.' for i,value in enumerate(options[:12]))
            if question.get('method') == 'confirm': suffix='Responde sí confirmo o no.'
            self.speak('Gentle Shell pregunta: '+str(question.get('title') or question.get('message') or 'Tu respuesta')+'. '+suffix)
    def answer_question(self,text):
        pending=list(self.runtime.dialogs.items())
        if not pending: return False
        identity,question=pending[0]; clean=normalize(text); record={'id':identity}
        if clean in ('cancelar pregunta','cancela la pregunta'): record['cancelled']=True
        elif question['method'] == 'confirm':
            if clean not in ('si confirmo','si','confirmo','no','no confirmo'): self.speak('Responde sí confirmo o no.'); return True
            record['confirmed']=clean in ('si confirmo','si','confirmo')
        elif question['method'] == 'select':
            options=question.get('options',[]); words={'uno':1,'una':1,'dos':2,'tres':3,'cuatro':4,'cinco':5,'seis':6,'siete':7,'ocho':8,'nueve':9,'diez':10}
            choice=clean.removeprefix('opcion '); index=int(choice) if choice.isdigit() else words.get(choice,0)
            value=options[index-1] if 1<=index<=len(options) else next((v for v in options if normalize(v)==clean),None)
            if value is None: self.speak('Dime el número o el texto de la opción.'); return True
            record['value']=value
        elif question['method'] in ('input','editor'): record['value']=text
        else: return False
        self.runtime.answer_dialog(record); return True
    def close(self):
        self.closed.set(); self.cancel_speech.set(); self.audio.interrupt()
        for thread in self.threads:
            if thread is not threading.current_thread(): thread.join(timeout=1)
