"""Native controls for the Gentle session displayed by the chat panel."""
import json
import os
from pathlib import Path
import shutil
import subprocess
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDialog, QFormLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget
from .task_dialog import TaskDialog


class ShellControls(QDialog):
    def __init__(self, panel):
        super().__init__(panel)
        self.panel = panel
        self.chat = panel.current_chat
        self.active = True
        self.finished.connect(lambda _: setattr(self, 'active', False))
        self.setWindowTitle('Gentle Shell')
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Gentle Shell · sesión actual'))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        self.form = QFormLayout(content)
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.profiles = QComboBox()
        self.form.addRow('Perfil', self.profiles)
        self.button('Usar perfil en este chat', self.apply_profile)
        self.button('Editar perfiles y asignar modelos por agente', lambda: self.command('/gentle:profiles'))
        self.button('Ver agentes y modelos disponibles', self.definitions)
        self.agents = QComboBox()
        self.form.addRow('Subagente de esta sesión', self.agents)
        self.button('Leer actividad', self.thread)
        self.button('Solicitar cancelación del subagente', self.cancel_agent)
        self.button('Actualizar listas', self.refresh)
        self.button('Gentle Voice · dictado', lambda: self.panel.run_command('/gentle:voice'))
        music = self.button('Gentle Music', lambda: self.panel.run_command('/gentle:music'))
        if os.name == 'nt':
            music.setEnabled(False)
            music.setText('Gentle Music · pendiente en Windows')
        self.button('Todos los comandos…', lambda: self.panel.refresh_commands(True))
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.PlainText)
        layout.addWidget(self.status)
        self.button('Cerrar', self.reject)

    def button(self, label, callback):
        button = QPushButton(label)
        self.form.addRow(button)
        button.clicked.connect(lambda: callback())
        return button

    def command(self, text):
        if self.active and self.chat == self.panel.current_chat:
            self.panel.run_command(text)

    def call(self, method, params, done, fallback=None):
        if self.chat != self.panel.current_chat or not self.active:
            return
        def receive(reply):
            if self.chat != self.panel.current_chat or not self.active:
                return
            if reply['supported']:
                done(reply['data'])
            elif fallback:
                fallback()
            else:
                self.status.setText('Este método no está disponible en la sesión.')
        self.panel.controller.background(
            lambda: self.panel.runtime.shell_control(self.chat, method, params), receive,
            lambda err: self.status.setText(str(err)) if self.active else None)

    def refresh(self):
        def profiles(data):
            current = self.profiles.currentText()
            self.profiles.clear()
            value = data.get('value', {})
            self.profiles.addItems(list(value.get('profiles', {})))
            self.profiles.setCurrentText(current or value.get('active', ''))
            if not self.profiles.count():
                self.status.setText('Crea un perfil en «Editar perfiles y asignar modelos por agente».')
        def agents(data):
            current = self.agents.currentData()
            self.agents.clear()
            for row in data.get('agents', []):
                self.agents.addItem(f"{row['agent']} · {row['status']} · {row.get('model') or 'heredado'}", row['id'])
            if self.agents.findData(current) >= 0:
                self.agents.setCurrentIndex(self.agents.findData(current))
        self.call('get_config', {'store':'profiles'}, profiles)
        self.call('list_subagents', {}, agents)

    def confirm(self, title, message, callback):
        box = TaskDialog({'method':'confirm','title':title,'message':message}, self.panel)
        box.accepted.connect(lambda: callback() if self.active and self.chat == self.panel.current_chat else None)
        self.panel.embed(box)

    def apply_profile(self):
        profile = self.profiles.currentText()
        if not profile:
            self.command('/gentle:profiles')
            return
        params = {'profile':profile, 'mode':'session'}
        def applied(data):
            if data.get('status') == 'confirmation_required':
                confirm = data['confirmation']
                self.confirm(confirm['title'], confirm['message'], lambda: self.call(
                    'apply_profile', {**params, 'confirmation':confirm['token']}, applied))
            else:
                self.status.setText('\n'.join([str(data.get('status', '')), *(n['text'] for n in data.get('notes', []))]))
        self.call('apply_profile', params, applied, lambda: self.command('/gentle:profiles'))

    def definitions(self):
        def show(data):
            rows = [f"{a['name']} · {a.get('model') or 'heredado'} · {a.get('thinking') or 'predeterminado'}"
                    for a in data.get('agents', [])]
            self.status.setText('\n'.join(rows) or 'Sin agentes definidos.')
        self.call('list_agent_definitions', {}, show, lambda: self.command('/gentle:profiles'))

    def thread(self):
        identity = self.agents.currentData()
        if not identity:
            self.command('/gentle:agents')
            return
        def show(data):
            lines = [str(item.get('text') or item.get('summary') or item.get('kind', ''))
                     for item in data.get('items', []) if item.get('kind') != 'thinking']
            self.status.setText('\n'.join(lines) or 'Sin actividad registrada.')
        self.call('get_subagent_thread', {'id':identity}, show, lambda: self.command('/gentle:agents'))

    def cancel_agent(self):
        identity = self.agents.currentData()
        if identity:
            self.confirm('Cancelar subagente', self.agents.currentText(), lambda: self.call(
                'cancel_subagent', {'id':identity}, lambda _: self.refresh(), lambda: self.command('/gentle:agents')))


def music_control(action):
    """Drive the same gentle-stream ctl interface as gentle-shell-gpui."""
    if os.name == 'nt':
        raise RuntimeError('Gentle Music está pendiente en Windows.')
    if action not in ('start', 'toggle', 'next', 'stop', 'status'):
        raise ValueError('Control de música desconocido.')
    player = shutil.which('gentle-stream')
    if not player:
        installed = Path.home()/'.gentle-shell/music/bin/gentle-stream'
        if not installed.is_file():
            raise RuntimeError('Instala gentle-stream con soporte para ctl --json para usar Gentle Music.')
        player = str(installed)
    result = subprocess.run([player, 'ctl', action, '--json'], capture_output=True, text=True, timeout=30)
    try:
        reply = json.loads(result.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        raise RuntimeError(result.stderr.strip()[:400] or 'El reproductor no devolvió un estado válido.') from None
    if result.returncode or not reply.get('ok'):
        raise RuntimeError(str(reply.get('error') or 'El reproductor no pudo completar la solicitud.'))
    return json.dumps(reply.get('state', reply), ensure_ascii=False)
