"""UI-owned Parakeet dictation. Produces a draft, never an agent instruction."""
import json
import os
from pathlib import Path
import shutil
from datetime import datetime, timezone

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, QTimer, Signal


ERRORS = {
    'node-version': 'El dictado necesita Node 22 o superior. Actualiza Gentle Shell.',
    'unsupported': 'Parakeet no está disponible para esta plataforma.',
    'no-input-device': 'No se encontró micrófono. Selecciona uno predeterminado en Windows.',
    'unsupported-input': 'El formato del micrófono predeterminado no es compatible.',
    'device-open': 'Apertura: no se pudo abrir el micrófono predeterminado. Cierra otras apps de audio y revisa el dispositivo y el acceso al micrófono en Windows.',
    'capture': 'Captura: el flujo de audio falló después de abrirse. Revisa la conexión del micrófono y otras apps de audio; no implica por sí solo un fallo de permisos.',
    'model-load': 'Carga del modelo: Parakeet no pudo cargarse. Libera memoria y, si persiste, repara el dictado desde el menú.',
    'decode': 'Transcripción: Parakeet no pudo procesar el audio. Reintenta una frase corta; si persiste, repara el dictado.',
    'not-installed': 'Resolución del modelo: faltan archivos. Repara el dictado desde el menú.',
    'worker-exited': 'El motor local se cerró inesperadamente. Revisa Node y las dependencias del runtime.',
    'protocol': 'El motor local devolvió una respuesta inválida. Repara el dictado.',
    'runtime-load': 'No se pudo cargar el audio. En Windows revisa Microsoft Visual C++ Runtime.',
    'empty-audio': 'No se grabó audio. Espera a ver «Escuchando» antes de hablar.',
    'no-speech': 'No reconocí palabras. Pulsa el micrófono para intentarlo de nuevo.',
    'model-invalid': 'El modelo no superó la verificación. Repara el dictado desde el menú.',
    'runtime-invalid': 'El motor no superó la verificación. Repara el dictado desde el menú.',
    'http': 'No se pudo descargar el dictado. Revisa Internet y vuelve a pulsar el micrófono.',
    'redirect': 'El servidor de descarga cambió. Se detuvo la descarga por seguridad.',
    'integrity': 'La descarga no superó la verificación. Vuelve a intentarlo.',
    'timeout': 'El dictado tardó demasiado. Vuelve a intentarlo.',
}


class Dictation(QObject):
    state_changed = Signal(str)
    message = Signal(str)
    transcript = Signal(str, str)
    finished = Signal()

    def __init__(self, root, parent=None):
        super().__init__(parent)
        self.root = Path(root) / 'dictation' / 'voice'
        self.history_path = self.root.parent / 'history.json'
        try:
            rows = json.loads(self.history_path.read_text(encoding='utf-8'))
            self.history = [r for r in rows[-100:] if isinstance(r, dict)] if isinstance(rows, list) else []
        except (OSError, ValueError):
            self.history = []
        self.download_component = 'Parakeet TDT 0.6B v3 + runtime'
        self.process = None
        self.state = 'idle'
        self.context = ''
        self.buffer = b''
        self.cancelled = False
        self.received_final = False

    def record_event(self, status, *, code='', received=None, total=None):
        # Closed fields only: never persist worker stderr, audio, transcript or prompts.
        row = {'time': datetime.now(timezone.utc).isoformat(timespec='seconds'),
               'component': self.download_component, 'status': status, 'stage': self.state}
        if code: row['code'] = code if code in ERRORS else 'internal'
        if received is not None:
            row.update(received=max(0, received), total=max(0, total))
        if status == 'progress' and self.history and self.history[-1].get('status') == 'progress' and self.history[-1].get('component') == self.download_component:
            self.history[-1] = row
        else:
            self.history.append(row)
        self.history = self.history[-100:]
        try:
            self.history_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.history_path.with_suffix('.tmp')
            temporary.write_text(json.dumps(self.history, ensure_ascii=False), encoding='utf-8')
            os.replace(temporary, self.history_path)
        except OSError:
            pass  # History failure must not lose the current draft or interrupt capture.

    def history_text(self):
        lines = [f'Destino local de modelos y runtime: {self.root}',
                 'Solo diagnóstico; no se guardan audio ni transcripciones.', '']
        for row in self.history:
            progress = f" · {row['received']/1048576:.1f}/{row['total']/1048576:.1f} MB" if 'received' in row else ''
            lines.append(f"{row.get('time', '')} · {row.get('component', '')} · {row.get('status', '')} · {row.get('stage', '')}{progress}")
            if row.get('code'): lines.append(ERRORS.get(row['code'], 'Fallo interno del dictado.'))
        return '\n'.join(lines) if self.history else '\n'.join(lines) + 'Todavía no hay operaciones registradas.'

    @property
    def active(self):
        return self.state != 'idle'

    def set_state(self, state):
        self.state = state
        self.state_changed.emit(state)

    def start(self, config, context, script=None, repair=False):
        if self.process is not None:
            return
        command = config.get('pi_command', [])
        candidate = command[0] if isinstance(command, list) and command else ''
        node = candidate if Path(candidate).stem.lower() == 'node' and Path(candidate).is_file() else shutil.which('node')
        if not node:
            self.message.emit('No se encontró Node. Usa Detectar Pi y Gentle Shell en Ajustes.')
            self.set_state('idle'); self.finished.emit(); return
        self.context = context; self.buffer = b''; self.cancelled = False; self.received_final = False
        process = QProcess(self); self.process = process
        env = QProcessEnvironment()
        # No API keys, NODE_OPTIONS or loader overrides enter the helper.
        for key in ('HOME','USERPROFILE','SystemRoot','SYSTEMROOT','windir','TEMP','TMP','TMPDIR','XDG_RUNTIME_DIR','PULSE_SERVER','PULSE_COOKIE','LANG','LC_ALL','LC_CTYPE'):
            if key in os.environ: env.insert(key, os.environ[key])
        env.insert('NODE_NO_WARNINGS','1')
        process.setProcessEnvironment(env)
        process.setWorkingDirectory(str(Path(node).resolve().parent))
        process.readyReadStandardOutput.connect(lambda: self.read_output(process))
        process.readyReadStandardError.connect(lambda: process.readAllStandardError())
        process.finished.connect(lambda *_: self.complete(process))
        process.errorOccurred.connect(lambda _: self.complete(process) if process.state() == QProcess.NotRunning else None)
        self.download_component = 'Parakeet TDT 0.6B v3 + runtime'
        self.set_state('starting')
        self.record_event('started')
        bridge = script or Path(__file__).parent / 'resources/parakeet/bridge.mjs'
        process.start(node, [str(bridge), str(self.root.resolve())] + (['--repair'] if repair else []))

    def read_output(self, process):
        raw = bytes(process.readAllStandardOutput())
        if process is not self.process or self.cancelled or self.received_final:
            return
        self.buffer += raw
        if len(self.buffer) > 256 * 1024:
            self.message.emit('Respuesta de dictado inválida.'); self.cancel(); return
        while b'\n' in self.buffer:
            line, self.buffer = self.buffer.split(b'\n', 1)
            if self.received_final: break
            try:
                data = json.loads(line)
                if not isinstance(data, dict): raise ValueError()
                kind = data.get('type')
                if kind == 'state' and data.get('state') in ('starting','installing','recording','transcribing'):
                    # Once stop/cancel is requested no late event may re-enable recording.
                    if self.state != 'cancelling': self.set_state(data['state'])
                elif kind == 'download' and data.get('component') in ('model', 'runtime'):
                    self.download_component = 'Parakeet TDT 0.6B v3' if data['component'] == 'model' else 'sherpa-onnx / node-cpal runtime'
                    self.record_event('download-started')
                elif kind == 'download-complete' and data.get('component') in ('model', 'runtime'):
                    self.record_event('download-verified')
                elif kind == 'progress':
                    received, total = int(data['received']), int(data['total'])
                    self.record_event('progress', received=received, total=total)
                    self.message.emit(f'Preparando dictado local: {received/1048576:.0f} / {total/1048576:.0f} MB. Pulsa el micrófono para cancelar.')
                elif kind == 'installed':
                    self.record_event('installed')
                    self.received_final = True
                    self.message.emit('Dictado listo. Pulsa el micrófono para hablar. Usa el micrófono predeterminado de Windows.')
                elif kind == 'result':
                    text = data.get('text')
                    if not isinstance(text, str) or len(text) > 16384: raise ValueError()
                    self.received_final = True
                    self.record_event('transcribed')
                    self.transcript.emit(self.context, text.strip())
                    if data.get('truncated'): self.message.emit('Se alcanzaron 2 minutos. El texto quedó en el borrador.')
                elif kind == 'error':
                    self.record_event('failed', code=data.get('code', 'internal'))
                    self.received_final = True
                    self.message.emit(ERRORS.get(data.get('code'), 'No se pudo completar el dictado. Tu borrador se conserva; vuelve a intentarlo.'))
            except (ValueError, TypeError, KeyError):
                self.message.emit('Respuesta de dictado inválida.'); self.cancel(); return

    def stop(self):
        if self.process is not None and self.state == 'recording':
            self.set_state('transcribing')
            self.process.write(b'stop\n')

    def cancel(self):
        self.cancelled = True
        process = self.process
        if process is None:
            self.set_state('idle'); return
        self.set_state('cancelling'); process.write(b'cancel\n')
        QTimer.singleShot(4000, lambda: self.kill(process) if process is self.process else None)

    def kill(self, process):
        # Include the native worker if it is blocked in synchronous recognition.
        if process.state() != QProcess.NotRunning:
            import psutil
            try:
                children = psutil.Process(process.processId()).children(recursive=True)
                for child in children:
                    try: child.kill()
                    except psutil.Error: pass
            except psutil.Error: pass
            process.kill()

    def complete(self, process):
        if process is not self.process: return
        self.read_output(process)
        if self.cancelled:
            self.record_event('cancelled')
        if not self.cancelled and not self.received_final:
            self.record_event('failed', code='worker-exited')
            self.message.emit('El proceso de dictado se cerró. Tu borrador se conserva; revisa Node y el micrófono.')
        self.process = None; self.set_state('idle'); self.finished.emit(); process.deleteLater()

    def close(self):
        self.cancelled = True
        if self.process is not None:
            self.kill(self.process)
            self.process.waitForFinished(1000)
