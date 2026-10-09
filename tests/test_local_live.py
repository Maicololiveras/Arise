import threading
import time
import unittest
from types import SimpleNamespace
from arise_app.local_voice import LocalVoiceBridge

def wait_for(predicate):
    deadline=time.monotonic()+2
    while time.monotonic()<deadline:
        if predicate():return
        time.sleep(.01)
    raise AssertionError('Local voice event timed out')

class LocalLiveTests(unittest.TestCase):
    def setUp(self):
        self.active=threading.Event();self.active.set();self.shutdown=threading.Event()
        self.calls=[];self.events=[];self.spoken=[];self.speaking=threading.Event();self.cancelled=threading.Event()
        self.runtime=SimpleNamespace(conversation='chat-one',tasks={},dialogs={},emit=lambda kind,data:self.events.append((kind,data)),stop=lambda:self.calls.append('stop'))
        def steer(text):
            self.calls.append(text);self.runtime.tasks.setdefault('task-one',{'status':'running','output':'','error':''});return {'task_id':'task-one','steering':len(self.calls)>1}
        self.runtime.steer=steer
        def say(text,cancel):
            self.spoken.append(text);self.speaking.set()
            if text=='respuesta larga':
                if cancel.wait(2):self.cancelled.set()
        self.bridge=LocalVoiceBridge(self.runtime,SimpleNamespace(interrupt=lambda:None),say,self.active,self.shutdown)
    def tearDown(self):self.bridge.close()
    def test_correction_while_task_runs_uses_same_task_and_latest_reply(self):
        self.bridge.submit('crea el proyecto');wait_for(lambda:len(self.calls)==1)
        self.bridge.submit('mejor en la otra carpeta');wait_for(lambda:len(self.calls)==2)
        self.assertEqual(self.calls,['crea el proyecto','mejor en la otra carpeta'])
        self.runtime.tasks['task-one'].update(status='completed',output='hecho en la otra carpeta')
        wait_for(lambda:self.spoken==['hecho en la otra carpeta'])
        self.assertEqual(len(self.runtime.tasks),1)
    def test_interrupt_audio_preserves_task_and_new_chat_drops_late_audio(self):
        self.bridge.speak('respuesta larga');wait_for(self.speaking.is_set)
        self.bridge.interrupt();wait_for(self.cancelled.is_set)
        self.assertNotIn('stop',self.calls)
        self.bridge.submit('continúa con lo anterior');wait_for(lambda:len(self.calls)==1)
        self.runtime.conversation='chat-two';self.runtime.tasks['task-one'].update(status='completed',output='resultado viejo')
        time.sleep(.1);self.assertNotIn('resultado viejo',self.spoken)
    def test_stop_audio_and_stop_task_are_distinct(self):
        self.bridge.submit('deja de hablar');time.sleep(.1);self.assertEqual(self.calls,[])
        self.bridge.submit('cancela la tarea');wait_for(lambda:self.calls==['stop'])
    def test_native_gentle_question_is_answered_by_voice_not_model(self):
        answers=[]
        self.runtime.dialogs['choice']={'method':'select','title':'Elige carpeta','options':['Proyecto uno','Proyecto dos']}
        def answer(record):answers.append(record);self.runtime.dialogs.pop(record['id'])
        self.runtime.answer_dialog=answer;self.bridge.poll_questions()
        wait_for(lambda:bool(self.spoken));self.assertIn('Opción 2: Proyecto dos',self.spoken[0])
        self.bridge.submit('opción dos');wait_for(lambda:bool(answers))
        self.assertEqual(answers[0],{'id':'choice','value':'Proyecto dos'});self.assertEqual(self.calls,[])
