"""Exact, user-originated voice controls, independent of model/tool latency."""
import re
import unicodedata
from contextlib import nullcontext


def command(text):
    if not isinstance(text, str): return None
    clean = ''.join(c for c in unicodedata.normalize('NFD', text.casefold()) if unicodedata.category(c) != 'Mn')
    clean = ' '.join(re.sub(r'[^\w\s]', ' ', clean).split())
    clean = re.sub(r'^(?:ari|arise)\s+', '', clean)
    clean = re.sub(r'\s+(?:por favor|please)$', '', clean)
    phrases = {
        'speech': ('deja de hablar', 'silencio', 'para de hablar', 'stop speaking', 'be quiet'),
        'end': ('termina la conversacion', 'terminar conversacion', 'deja de escuchar', 'para de escuchar', 'stop listening', 'end conversation'),
        'stop': ('cancela la tarea', 'detente', 'cancelar', 'deten la tarea', 'cancel task', 'stop task', 'stop'),
        'shutdown': ('apagate', 'cierra arise', 'cerrar arise', 'shut down', 'quit arise', 'turn off'),
        'study_start': ('modo estudio', 'inicia modo estudio', 'vamos a estudiar', 'modo cuestionario', 'study mode', 'start studying', 'quiz mode', 'vamos a responder preguntas', 'vamos a entrar en modo cuestionario'),
        'study_pause': ('pausa el estudio', 'pausa modo estudio', 'pause study'),
        'study_resume': ('reanuda el estudio', 'continua modo estudio', 'resume study'),
        'study_end': ('termina el estudio', 'termina modo estudio', 'end study'),
    }
    return next((action for action, choices in phrases.items() if clean in choices), None)


def dispatch(runtime, text, conversation, chat_generation, interrupt, end):
    action = command(text)
    if not action: return False
    with getattr(runtime, 'transition_lock', nullcontext()):
        if runtime.conversation != conversation or getattr(runtime, 'chat_generation', 0) != chat_generation:
            return True  # stale controls never affect a newly opened chat
        runtime.emit('voice_transcript', {'role': 'user', 'text': text})
        interrupt()
        if action == 'end': end()
        elif action == 'stop': runtime.stop()
        elif action == 'shutdown':
            end()
            runtime.request_shutdown()
        elif action.startswith('study_'):
            operation = action.removeprefix('study_')
            if operation == 'start':
                # Voice opens the consent/options dialog; never silently starts capture.
                runtime.emit('study_setup', {})
            else: runtime.study_control(operation)
        return True
