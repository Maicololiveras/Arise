"""Native ARISE orb, setup, conversation panel and tray. No embedded browser."""
from __future__ import annotations
from .updates import application_name
import argparse
import base64
import html
import json
import os
import sys
import threading
import time
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QObject, Signal, QEvent, QPoint, QSize, QBuffer, QIODevice, QUrl
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QImage, QDesktopServices, QShortcut, QKeySequence
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import (QPlainTextEdit, QApplication, QWidget, QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QTextBrowser, QTextEdit, QComboBox, QCheckBox, QTabWidget,
    QFileDialog, QMessageBox, QSystemTrayIcon, QMenu, QSpinBox, QDialogButtonBox, QInputDialog, QWidgetAction, QScrollArea, QProgressDialog, QSizePolicy)
from .orb import build_orb
from .assistant import Assistant
from .audio import Audio
from .voice import VoiceService
from .server import make_server
from .hotkeys import Hotkeys
from .bundle import configure_bundle

class ConnectionNotice(QLabel):
    """One quiet, fixed-height line for real runtime notices, outside the chat."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.full_text = ''
        self.setTextFormat(Qt.PlainText)
        self.setFixedHeight(20)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.setStyleSheet('color:#9DB3C7;font-size:11px;padding:0 3px;')
        self.set_notice('')

    def set_notice(self, text):
        self.full_text = ' '.join(str(text).split())
        self.setToolTip(self.full_text)
        self.setAccessibleName('Estado de conexión y herramientas')
        self.setAccessibleDescription(self.full_text)
        self.refresh_text()

    def refresh_text(self):
        self.setText(self.fontMetrics().elidedText(self.full_text, Qt.ElideRight, max(0,self.width()-6)))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.refresh_text()


STYLE = """
QWidget {background:#0A1828;color:#EDF8FF;font-family:'Segoe UI';font-size:13px;}
QDialog {background:#0A1828;}
QLineEdit,QTextEdit,QTextBrowser,QComboBox,QSpinBox {background:#10283C;border:1px solid #25445B;border-radius:7px;padding:8px;selection-background-color:#2563EB;}
QPushButton {background:#14394A;border:1px solid #2F6878;border-radius:7px;padding:9px 16px;}
QPushButton:hover {background:#205368;} QPushButton:disabled {color:#7292A8;}
QLabel#title {font-size:24px;font-weight:700;color:#74F6FF;}
QLabel#chatTitle {font-size:18px;font-weight:600;color:#EDF8FF;}
QLabel#chatStatus,QLabel#chatPrivacy {font-size:11px;color:#9DB3C7;}
QTextBrowser#chatHistory {background:transparent;border:0;padding:6px;font-size:15px;}
QPushButton#iconButton {padding:6px;border:0;background:transparent;border-radius:8px;}
QPushButton#iconButton:hover {background:#17364C;}
QPushButton#iconButton:checked {background:#205368;border:1px solid #74F6FF;}
QTabWidget::pane {border:1px solid #25445B;} QTabBar::tab {padding:12px;background:#10283C;}
QTabBar::tab:selected {color:#74F6FF;background:#17364C;}
QCheckBox {padding:5px;} QMenu {background:#10283C;}
"""

class WheelSafeCombo(QComboBox):
    def wheelEvent(self,event):event.ignore()

class WheelSafeSpin(QSpinBox):
    def wheelEvent(self,event):event.ignore()

class Worker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def start(self, operation):
        def run():
            try:
                self.finished.emit(operation())
            except Exception as error:
                self.failed.emit(str(error)[:600])
        threading.Thread(target=run, daemon=True).start()


class ChatInput(QTextEdit):
    submitted = Signal()
    image_pasted = Signal(QImage)

    def canInsertFromMimeData(self, source):
        return source.hasImage() or super().canInsertFromMimeData(source)

    def insertFromMimeData(self, source):
        if source.hasImage():
            image = QImage(source.imageData())
            if not image.isNull(): self.image_pasted.emit(image)
        else: super().insertFromMimeData(source)


    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not event.modifiers() & Qt.ShiftModifier:
            self.submitted.emit()
            event.accept()
        else:
            super().keyPressEvent(event)


def control_icon(name):
    """One vector icon family, independent of platform emoji fonts."""
    paths = {
        "menu": '<path d="M4 6h16M4 12h16M4 18h16"/>',
        "folder": '<path d="M3 7V5h7l2 2h9v13H3Z"/>',
        "settings": '<path d="m9 3-.5 3-2 1-2.8-1-2 3 2.3 2v2L1.7 15l2 3 2.8-1 2 1 .5 3h4l.5-3 2-1 2.8 1 2-3-2.3-2v-2l2.3-2-2-3-2.8 1-2-1-.5-3Z"/><circle cx="11" cy="12" r="3"/>',
        "send": '<path d="m3 3 18 9-18 9 3-9ZM6 12h15"/>',
        "wave": '<path d="M3 10v4M7 6v12M12 3v18M17 6v12M21 10v4"/>',
        "mic": '<rect x="9" y="2" width="6" height="13" rx="3"/><path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3M8 22h8"/>',
        "mic-up": '<rect x="5" y="7" width="6" height="10" rx="3"/><path d="M2 12v2a6 6 0 0 0 12 0M8 20v2M5 22h6M19 12V2m-3 3 3-3 3 3"/>',
        "stop": '<rect x="5" y="5" width="14" height="14" rx="2"/>',
        "plus": '<path d="M12 4v16M4 12h16"/>',
    }
    from PySide6.QtSvg import QSvgRenderer
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="#B9D6E7" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">' + paths[name] + '</g></svg>'
    pix = QPixmap(24, 24); pix.fill(Qt.transparent)
    painter = QPainter(pix); QSvgRenderer(svg.encode()).render(painter); painter.end()
    return QIcon(pix)


def icon():
    from .brand import icon_image
    result = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        result.addPixmap(QPixmap.fromImage(icon_image(size)))
    return result

class Settings(QDialog):
    saved = Signal()
    def __init__(self, controller):
        super().__init__()
        self.controller, self.runtime = controller, controller.runtime
        self.setWindowTitle("ARISE · Configuración")
        self.resize(760, 650); self.setStyleSheet(STYLE)
        layout = QVBoxLayout(self)
        title = QLabel("Configura tu ARISE"); title.setObjectName("title"); layout.addWidget(title)
        intro=QLabel("Elige voz, conecta el agente y habilita las herramientas que usarás.");intro.setWordWrap(True);layout.addWidget(intro)
        quick_setup=QPushButton("Configurar todo desde ZIP")
        quick_setup.clicked.connect(controller.install_model_pack);layout.addWidget(quick_setup)
        gentle_setup=QPushButton("Configurar / reparar Gentle integrado")
        gentle_setup.clicked.connect(controller.install_gentle);layout.addWidget(gentle_setup)
        native_setup=QPushButton("Avanzado: instalador externo de Gentle AI · QA")
        native_setup.clicked.connect(controller.install_gentle_native);layout.addWidget(native_setup)
        connections=QPushButton('Conexiones, celular y recordatorios · QA')
        connections.clicked.connect(self.show_connections);layout.addWidget(connections)
        from .platforms import native_preview, has_vosk
        if native_preview():
            notice = QLabel("Versión nativa de prueba: actualización manual; herramientas de escritorio y modelos offline no incluidos. Consulta la guía de esta distribución.")
            notice.setWordWrap(True); layout.addWidget(notice)
            native_setup.setEnabled(False)
            quick_setup.setEnabled(False)
        tabs = QTabWidget(); layout.addWidget(tabs)
        self.fields, self.keys, self.mcp = {}, {}, {}
        config = self.runtime.storage.config
        language_row = QHBoxLayout()
        language_row.addWidget(QLabel('Idioma de la interfaz'))
        self.language_choice = QComboBox(); self.language_choice.addItem('Español', 'es'); self.language_choice.addItem('English', 'en')
        self.language_choice.setCurrentIndex(max(0,self.language_choice.findData(config.get('ui_language','es'))))
        language_row.addWidget(self.language_choice); layout.insertLayout(1, language_row)
        self.language_choice.setAccessibleName("Idioma de la interfaz")
        self.language_choice.currentIndexChanged.connect(lambda: controller.change_language(self.language_choice.currentData()))
        voice = QWidget(); f = QFormLayout(voice); tabs.addTab(voice, "Conversación de voz")
        dictation_help = QLabel("Dictado al borrador: Parakeet TDT 0.6B v3 local, micrófono predeterminado del sistema. Es independiente de los modelos de conversación configurados aquí.")
        dictation_help.setWordWrap(True); f.addRow(dictation_help)
        self.fields["voice_provider"] = WheelSafeCombo(); self.fields["voice_provider"].addItems(["local", "forge-local", "forge-openai", "openai", "gemini"])
        self.fields["voice_provider"].setCurrentText(config["voice_provider"])
        f.addRow("Proveedor", self.fields["voice_provider"])
        realtime_help = QLabel("OpenAI / Gemini: conversa mientras Gentle Shell trabaja. Puedes consultar, corregir o cancelar una tarea. Las aprobaciones permanecen en el panel. Las voces del proveedor son distintas de Gonzalo.")
        realtime_help.setWordWrap(True)
        f.addRow(realtime_help)
        self.fields['forge_voice']=WheelSafeCombo();self.fields['forge_voice'].addItem('es-CO-GonzaloNeural');f.addRow('Gonzalo · español de Colombia',self.fields['forge_voice'])
        self.text_field(f,'forge_rate','Velocidad Forge',config['forge_rate'])
        pause=WheelSafeSpin();pause.setRange(700,3000);pause.setSingleStep(100);pause.setSuffix(' ms');pause.setValue(config['voice_silence_ms'])
        self.fields['voice_silence_ms']=pause;f.addRow('Pausa para terminar el dictado',pause)
        preset=QPushButton('Usar Gonzalo · Colombia · +5%');preset.clicked.connect(self.select_gonzalo);f.addRow(preset)
        f.addRow(QLabel('Gonzalo necesita Internet. La prueba de salida no activa el micrófono.'))
        self.check_field(f,'voice_windows_fallback','Usar voz de Windows si Gonzalo falla (con aviso)',config.get('voice_windows_fallback',True))
        self.fields['voice_windows_fallback'].setEnabled(os.name == 'nt')
        self.button(f,'Probar solo la salida de voz',self.preview_voice)
        self.button(f,'Detener prueba de voz',lambda:self.controller.voice.end_session())
        self.fields["local_stt_engine"] = WheelSafeCombo(); self.fields["local_stt_engine"].addItems(["auto", "vosk", "faster-whisper", "openai-whisper"])
        self.fields["local_stt_engine"].setCurrentText(config["local_stt_engine"]); f.addRow("Motor local", self.fields["local_stt_engine"])
        for key, label in (("voice_model", "Modelo de voz"), ("voice", "Voz de otros proveedores"), ("wake_model", "Modelo Vosk (carpeta)"), ("local_stt_model", "Modelo local (.pt o carpeta)"), ("piper_model", "Modelo Piper (.onnx)")):
            self.text_field(f, key, label, config[key])
        self.voice_form=f
        f.setRowVisible(self.fields['voice'],config['voice_provider']!='local' or config['local_tts']=='system')
        self.fields["voice_provider"].currentTextChanged.connect(self.provider_changed)
        devices = []
        try:
            devices = Audio.devices()
        except Exception:
            f.addRow(QLabel("No se detectaron dispositivos. Revisa el audio del sistema."))
        for key, label, capability in (("input_device", "Micrófono", "input"), ("output_device", "Altavoz", "output")):
            combo = WheelSafeCombo(); combo.addItem("Predeterminado del sistema", None)
            for device in devices:
                if device[capability]:
                    combo.addItem(device["name"], device["id"])
            idx = combo.findData(config[key]); combo.setCurrentIndex(max(0, idx)); self.fields[key] = combo; f.addRow(label, combo)
        f.addRow(QLabel("local: modo ligero sin GPU. forge-local: voz a voz nativa con servidor local compatible. forge-openai: voz a voz en línea."))
        self.text_field(f,'forge_voice_url','Servidor de voz a voz local',config['forge_voice_url'])
        for key,label,choices in [('voice_task_engine','Motor de conversación',['gentle','local-dialogue']),('local_profile','Perfil de memoria',['auto','light','standard']),('local_tts','Salida de voz local',['forge','system'])]:
            combo=WheelSafeCombo();combo.addItems(choices);combo.setCurrentText(config[key]);self.fields[key]=combo;f.addRow(label,combo)
        self.fields['local_tts'].currentTextChanged.connect(lambda value:self.voice_form.setRowVisible(self.fields['voice'],self.fields['voice_provider'].currentText()!='local' or value=='system'))
        self.check_field(f, 'local_dialogue_enabled' , 'Conversar con un modelo local mientras Gentle trabaja', config['local_dialogue_enabled'])
        self.text_field(f,'local_dialogue_url','Servidor conversacional local',config['local_dialogue_url'])
        self.text_field(f,'local_server_command','Arranque local (JSON)',json.dumps(config['local_server_command']))
        self.text_field(f,'local_dialogue_model','Modelo local (vacío: detectar)',config['local_dialogue_model'])
        self.check_field(f, "local_barge_in", "Permitir interrupciones en voz local", config["local_barge_in"])
        threshold=WheelSafeSpin(); threshold.setRange(300,10000); threshold.setValue(config["voice_interrupt_threshold"]); self.fields["voice_interrupt_threshold"]=threshold; f.addRow("Umbral de interrupción local",threshold)
        self.check_field(f, "wake_enabled", "Activar ARISE con una frase de voz (escucha local)", config["wake_enabled"])
        if not has_vosk():
            self.fields['wake_enabled'].setEnabled(False)
            self.fields['wake_enabled'].setToolTip('Vosk no está disponible para esta distribución. Usa una entrada de voz compatible.')
        self.check_field(f,"wake_open_panel","Abrir el panel al activar ARISE con la voz",config.get("wake_open_panel",True))
        self.text_field(f,"wake_reply","Respuesta al activar la voz local",config.get("wake_reply","Te escucho."))
        self.check_field(f,"voice_fluent","Voz fluida: preparar la siguiente frase mientras habla",config.get("voice_fluent",True))
        self.text_field(f, "wake_phrases", "Frases (separadas por coma)", ", ".join(config["wake_phrases"]))
        f.addRow(QLabel("Voz local con escucha continua e interrupciones. Usa auriculares para evitar que el micrófono capture la propia voz de ARISE."))
        self.button(f, "Elegir carpeta Vosk", lambda: self.pick("wake_model", directory=True))
        self.button(f, "Descargar activación local en español", self.download_wake)
        self.button(f, "Detectar mis modelos de voz", self.detect_voice_models)
        self.button(f, "Elegir carpeta faster-whisper", lambda: self.pick("local_stt_model", directory=True))
        self.button(f, "Elegir archivo Whisper .pt", lambda: self.pick("local_stt_model"))
        self.button(f, "Instalar solo modelo de activación", self.install_voice_pack)
        self.button(f, "Elegir modelo Piper", lambda: self.pick("piper_model"))
        self.button(f, "Probar conversación", self.test_voice)
        agent = QWidget(); f = QFormLayout(agent); tabs.addTab(agent, "Agente")
        self.fields['engine_mode'] = WheelSafeCombo()
        self.fields['engine_mode'].addItem('Integrado en ARISE (recomendado)', 'bundled')
        self.fields['engine_mode'].addItem('Instalación externa (avanzado)', 'external')
        self.fields['engine_mode'].setCurrentIndex(0 if config.get('engine_mode','bundled') == 'bundled' else 1)
        f.addRow('Motor del asistente', self.fields['engine_mode'])
        self.text_field(f, "preferred_name", "Cómo llamarte (vacío: usuario del PC)", config.get("preferred_name", ""))
        self.fields["preferred_name"].setMaxLength(80)
        self.fields["engine_mode"].setProperty("localizedItems", True)
        for key, label in (("workspace", "Carpeta de trabajo"), ("pi_command", "Comando Pi (lista JSON)"), ("gentle_path", "Carpeta Gentle Shell"), ("agent_provider", "Proveedor del agente"), ("agent_model", "Modelo del agente")):
            value = json.dumps(config[key]) if key == "pi_command" else config[key]
            self.text_field(f, key, label, value)
        self.fields["thinking"] = WheelSafeCombo(); self.fields["thinking"].addItems(["off", "minimal", "low", "medium", "high", "xhigh"])
        self.fields["thinking"].setCurrentText(config["thinking"]); f.addRow("Esfuerzo", self.fields["thinking"])
        self.check_field(f, "code_enabled", "Autorizar ejecución local en este chat", config["code_enabled"])
        note = QLabel("Incluye shell y subagentes de Gentle. La carpeta es el directorio inicial, no una sandbox. "
                      "Cada chat nuevo requiere autorización propia. Ocultar el panel o terminar la voz conserva la sesión.")
        note.setWordWrap(True); f.addRow(note)
        self.button(f, "Ver capacidades reales", self.show_capabilities)
        self.button(f, "Elegir carpeta de trabajo", lambda: self.pick("workspace", True))
        self.button(f, "Elegir Gentle Shell", lambda: self.pick("gentle_path", True))
        self.check_field(f, "antigravity_enabled", "Activar Antigravity Bridge", config.get("antigravity_enabled", False))
        agy_help = QLabel("Antigravity usa su propia cuenta de Google. Al activar y conectar puede descargar el servidor ACP (aprox. 1,5 GB). Guarda, conecta y usa /agy para acceder y diagnosticar; después lista los modelos. Requiere autorización de ejecución local para conversar. No importa credenciales externas.")
        agy_help.setWordWrap(True); f.addRow(agy_help)
        self.button(f, "Conectar con Antigravity", self.connect_antigravity)
        self.button(f, "Conectar y listar modelos", self.models)
        self.button(f, "Conectar cuenta y elegir modelo", self.accounts)
        self.button(f, "Detectar Pi y Gentle Shell", self.detect_agent)
        self.fields['memory_mode'] = WheelSafeCombo()
        self.fields['memory_mode'].addItem('Memoria privada de ARISE', 'private')
        self.fields['memory_mode'].addItem('Servidor local compartido de Engram', 'shared')
        self.fields['memory_mode'].setCurrentIndex(1 if config.get('memory_mode') == 'shared' else 0)
        self.fields['memory_mode'].setProperty('localizedItems', True)
        f.addRow('Memoria', self.fields['memory_mode'])
        memory_help = QLabel('La memoria compartida requiere un servidor compatible ya iniciado. No copia ni mezcla bases. El ejecutable privado guardado se conserva, pero no se usa en modo compartido. Aplicar y conectar memoria valida la selección y reconecta el agente sin cerrar la aplicación ni borrar el chat.')
        memory_help.setWordWrap(True); f.addRow(memory_help)
        self.memory_status = QLabel()
        f.addRow('Estado de memoria', self.memory_status)
        def refresh_memory():
            from .i18n import tr
            labels = {'configured':'Configurado', 'verifying':'Verificando', 'connected':'Conectado', 'error':'Error'}
            try:
                state = self.runtime.status().get('memory', {}).get('state', 'configured') if getattr(self.runtime, 'is_remote', False) else getattr(self.runtime, 'memory_state', 'configured')
            except Exception:
                state = 'error'
            if self.fields['memory_mode'].currentData() != self.runtime.storage.config.get('memory_mode', 'private'):
                state = 'configured'
            self.memory_status.setText(tr(labels.get(state, 'Error')))
        self.memory_connect = QPushButton('Aplicar y conectar memoria')
        self.memory_connect.clicked.connect(self.connect_memory)
        f.addRow(self.memory_connect)
        self.memory_timer = QTimer(self); self.memory_timer.timeout.connect(refresh_memory)
        self.memory_timer.start(1000); refresh_memory()
        self.text_field(f, 'engram_bin', 'Ejecutable Engram (vacío: detectar instalación oficial)', config.get('engram_bin',''))
        self.button(f, 'Actualizar / reinstalar Engram estable · QA', lambda: controller.update_dependencies(False))
        self.button(f, 'Actualizar Gentle, Pi y Engram y usar este entorno · QA', lambda: controller.update_dependencies(True))
        f.addRow(QLabel("Dejar proveedor/modelo vacíos conserva la selección existente de Pi."))
        keys = QWidget(); f = QFormLayout(keys); tabs.addTab(keys, "Credenciales")
        for provider in ("openai", "gemini", "anthropic", "github-updates", "local-dialogue", "forge-local"):
            entry = QLineEdit(); entry.setEchoMode(QLineEdit.Password); entry.setPlaceholderText("Dejar vacío conserva la clave existente")
            self.keys[provider] = entry; f.addRow(provider, entry)
        f.addRow(QLabel("Forge, ScreenView e InputControl no requieren GitHub. Transcripción privada sí requiere acceso; se detecta tu sesión de gh."))
        self.persist = QCheckBox("Guardar claves protegidas por Windows (DPAPI)"); self.persist.setChecked(os.name == "nt")
        f.addRow(self.persist)
        f.addRow(QLabel("Desmarcado: claves solo durante esta ejecución. Nunca se guardan en settings.json."))
        self.text_field(f, "gmail_client_file", "JSON OAuth Desktop de Google", config["gmail_client_file"])
        self.button(f, "Elegir JSON de Gmail", lambda: self.pick("gmail_client_file"))
        self.button(f, "Conectar Gmail", self.gmail_connect)
        self.button(f, "Desconectar Gmail", self.runtime.gmail.vault.clear)
        tools = QWidget(); f = QFormLayout(tools); tabs.addTab(tools, "Herramientas")
        for name, spec in config["mcp"].items():
            enabled = QCheckBox(name); enabled.setChecked(spec.get("enabled", False))
            command = QLineEdit(json.dumps(spec["command"], ensure_ascii=False))
            self.mcp[name] = (enabled, command)
            f.addRow(enabled, command)
        for name, label in (("forge", "Forge"), ("screenview", "ScreenView"), ("inputcontrol", "InputControl"), ("transcripcion", "Transcripción · requiere GitHub")):
            self.button(f, "Descargar / reparar " + label, lambda checked=False, name=name: self.setup_desktop_tools([name]))
        self.button(f, "Descargar las tres herramientas públicas", lambda: self.setup_desktop_tools())
        f.addRow(QLabel("Los paquetes aún no publicados se indicarán como pendientes. Se conserva tu instalación si una descarga falla."))
        self.button(f, "Guardar y comprobar herramientas", self.connect_tools)
        self.button(f, "Importar configuración MCP", self.import_tools)
        self.text_field(f, "extra_mcp", "MCP adicionales (objeto JSON)", "{}")
        f.addRow(QLabel("Los comandos son listas de ejecutables y argumentos; no cadenas de shell."))
        models = QWidget(); f = QFormLayout(models); tabs.addTab(models, "Descargas")
        intro = QLabel("Instala solo lo que necesitas. Al terminar se guardan las rutas y se configura cada componente automáticamente.")
        intro.setWordWrap(True); f.addRow(intro)
        for name, label in (("vosk", "Vosk español · activación · ~40 MB"), ("whisper", "Whisper small · transcripción · ~465 MB"), ("piper", "Piper español · voz y motor"), ("dialogue", "Qwen · conversación local y servidor · más de 1 GB")):
            self.button(f, "Descargar " + label, lambda checked=False, name=name: self.download_models([name]))
        self.button(f, "Descargar y configurar todos los modelos", lambda: self.download_models(["vosk", "whisper", "piper", "dialogue"]))
        self.button(f, "Instalar modelos desde ZIP existente", controller.install_model_pack)
        note = QLabel("Requiere conexión y espacio libre. Si falla, puedes reintentar; tu configuración anterior se conserva. Los modelos se descargan de sus fuentes oficiales.")
        note.setWordWrap(True); f.addRow(note)
        ui = QWidget(); f = QFormLayout(ui); tabs.addTab(ui, "Orbe")
        size = WheelSafeSpin(); size.setRange(48, 240); size.setValue(config["orb_size"]); self.fields["orb_size"] = size
        f.addRow("Tamaño", size)
        self.check_field(f,"desktop_auto_clear","Apartar el chat durante el control del escritorio",config.get("desktop_auto_clear",True))
        corner=WheelSafeCombo()
        for label,value in (("Abajo a la derecha","bottom-right"),("Abajo a la izquierda","bottom-left"),("Arriba a la derecha","top-right"),("Arriba a la izquierda","top-left")):corner.addItem(label,value)
        corner.setCurrentIndex(max(0,corner.findData(config.get("desktop_orb_corner","bottom-right"))))
        self.fields["desktop_orb_corner"]=corner;f.addRow("Esquina del orbe durante el control",corner)
        self.check_field(f, "pinned", "Orbe siempre visible", True); self.fields["pinned"].setEnabled(False)
        self.check_field(f, "reduced_motion", "Reducir animación", config["reduced_motion"])
        self.fields["orb_animation"] = WheelSafeCombo(); self.fields["orb_animation"].addItems(["sprite", "native"]); self.fields["orb_animation"].setCurrentText(config["orb_animation"]); f.addRow("Animación", self.fields["orb_animation"])
        autostart = QCheckBox("Iniciar ARISE al entrar a Windows")
        autostart.setEnabled(os.name == "nt" and getattr(sys, "frozen", False))
        autostart.setChecked(self.autostart_enabled()); self.autostart = autostart; f.addRow(autostart)
        self.button(f, "Abrir carpeta de datos", controller.open_data)
        pages = [(tabs.widget(i), tabs.tabText(i)) for i in range(tabs.count())]
        while tabs.count(): tabs.removeTab(0)
        for page, label in pages:
            form=page.layout()
            if isinstance(form,QFormLayout):
                form.setRowWrapPolicy(QFormLayout.WrapAllRows)
                form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
            for field in page.findChildren(QLabel):field.setWordWrap(True)
            for field in page.findChildren(QWidget):
                if isinstance(field,(QLineEdit,QComboBox)):
                    field.setMinimumWidth(0);field.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Fixed)
            scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); scroll.setWidget(page); tabs.addTab(scroll, label)
        self.message = QLabel(""); self.message.setWordWrap(True); layout.addWidget(self.message)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Close)
        buttons.button(QDialogButtonBox.Save).setText("Guardar"); buttons.button(QDialogButtonBox.Close).setText("Cerrar")
        buttons.accepted.connect(self.save); buttons.rejected.connect(self.close); layout.addWidget(buttons)

    def accounts(self):
        if not self.save(): return
        from .accounts_widget import AccountsDialog
        self.account_window=AccountsDialog(self.runtime, self)
        self.account_window.exec()
        self.account_window=None
        if getattr(self.runtime,'is_remote',False):
            self.runtime.storage.config=self.runtime.request('config')
        for key in ('agent_provider','agent_model'):
            self.fields[key].setText(self.runtime.storage.config[key])

    def show_connections(self):
        from .connections_widget import ConnectionsDialog
        dialog=ConnectionsDialog(self.runtime,self)
        dialog.exec()

    def closeEvent(self,event):
        if getattr(self,"account_window",None):self.account_window.reject()
        # Closing discards the unsaved form; storage changes only in Save.
        self.controller.settings_window=None
        event.accept();self.deleteLater()

    def text_field(self, form, key, label, value):
        field = QLineEdit(str(value)); self.fields[key] = field; form.addRow(label, field)

    def check_field(self, form, key, label, value):
        field = QCheckBox(); field.setAccessibleName(label); field.setChecked(value); self.fields[key] = field
        row=QWidget();layout=QHBoxLayout(row);layout.setContentsMargins(0,0,0,0);layout.addWidget(field)
        caption=QLabel(label);caption.setWordWrap(True);caption.setBuddy(field);layout.addWidget(caption,1);form.addRow(row)

    def button(self, form, label, callback):
        button = QPushButton(label); button.clicked.connect(callback); form.addRow(button)

    def pick(self, key, directory=False):
        value = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta") if directory else QFileDialog.getOpenFileName(self, "Seleccionar archivo")[0]
        if value:
            self.fields[key].setText(value)

    def select_gonzalo(self):
        self.fields['voice_provider'].setCurrentText('local')
        self.fields['local_tts'].setCurrentText('forge')
        self.fields['piper_model'].clear()
        self.fields['forge_voice'].setCurrentText('es-CO-GonzaloNeural');self.fields['forge_rate'].setText('+5%')
        self.message.setText('Gonzalo seleccionado. Pulsa Guardar para aplicarlo; requiere Forge y conexión a Internet.')

    def provider_changed(self, provider):
        self.voice_form.setRowVisible(self.fields['voice'],provider!='local' or self.fields['local_tts'].currentText()=='system')
        if provider in ("openai","forge-openai"):
            self.fields["voice_model"].setText("gpt-realtime-2.1"); self.fields["voice"].setText("marin")
        elif provider == "forge-local":
            self.fields["voice_model"].setText("modelo-local-voz"); self.fields["voice"].setText("default")
        elif provider == "gemini":
            self.fields["voice_model"].setText("gemini-3.1-flash-live-preview"); self.fields["voice"].setText("Aoede")
        else:
            self.fields["voice_model"].setText("local"); self.fields["voice"].setText("es-CO-GonzaloNeural")

    def changes(self):
        changes = {}
        for key, field in self.fields.items():
            if isinstance(field, QCheckBox): value = field.isChecked()
            elif isinstance(field, QSpinBox): value = field.value()
            elif isinstance(field, QComboBox): value = field.currentData() if key.endswith("_device") or key in ("engine_mode", "desktop_orb_corner", "memory_mode") else field.currentText()
            else: value = field.text().strip()
            changes[key] = value
        changes["pi_command"] = json.loads(changes["pi_command"])
        changes["local_server_command"] = json.loads(changes["local_server_command"])
        changes["wake_phrases"] = [v.strip().lower() for v in changes["wake_phrases"].split(",") if v.strip()]
        extra = json.loads(changes.pop("extra_mcp"))
        if not isinstance(extra, dict): raise ValueError("MCP adicionales debe ser un objeto JSON")
        changes["mcp"] = {**{name: {**self.runtime.storage.config["mcp"].get(name, {}), "command": json.loads(command.text()), "enabled": enabled.isChecked()} for name, (enabled, command) in self.mcp.items()}, **extra}
        changes["onboarding_complete"] = True
        return changes

    def save(self):
        try:
            self.controller.voice.end_session()
            if self.controller.voice.active.is_set():
                raise RuntimeError("Termina la conversación de voz antes de guardar.")
            from .memory_selection import validate
            if not getattr(self.runtime, "is_remote", False):
                validate({**self.runtime.storage.config, **self.changes()})
                from .antigravity import validate as validate_antigravity
                validate_antigravity({**self.runtime.storage.config, **self.changes()})
            for provider, field in self.keys.items():
                if field.text().strip():
                    self.runtime.credentials.save(provider, field.text().strip(), self.persist.isChecked())
                    field.clear()
            self.runtime.settings(self.changes())
            self.set_autostart(self.autostart.isChecked())
            self.controller.reconfigure()
            self.message.setText("Configuración guardada. Prueba la conversación y las conexiones.")
            self.saved.emit(); return True
        except Exception as error:
            self.message.setText(str(error)); return False

    def preview_voice(self):
        if not self.save():return
        self.message.setText('Preparando prueba de voz…')
        def operation():
            if getattr(self.runtime,'is_remote',False):return self.runtime.request('voice/preview',{},timeout=90)
            return self.controller.voice.preview()
        self.controller.background(operation,lambda result:self.message.setText('Prueba reproducida. Si no escuchaste audio, revisa la salida de Windows.' if result.get('played') else 'Prueba detenida.'),lambda error:self.message.setText(error))

    def test_voice(self):
        if self.save(): self.controller.wake("Saluda brevemente y confirma que escuchas.")

    def connect_memory(self):
        from .i18n import tr
        changes = {"memory_mode": self.fields["memory_mode"].currentData(),
                   "engram_bin": self.fields["engram_bin"].text().strip()}
        self.memory_connect.setEnabled(False)
        self.message.setText(tr("Verificando y conectando memoria…"))
        def operation():
            return self.runtime.connect_memory(changes)
        def done(result):
            self.memory_connect.setEnabled(True)
            self.message.setText(tr("Selección de memoria aplicada. Agente conectado; el estado Conectado se confirma al usar una herramienta de memoria."))
        def failed(error):
            self.memory_connect.setEnabled(True)
            self.message.setText(str(error))
        self.controller.background(operation, done, failed)

    def connect_antigravity(self):
        self.fields["antigravity_enabled"].setChecked(True)
        if not self.save(): return
        self.message.setText("Preparando Antigravity. Completa el acceso de Google y después elige un modelo con Conectar y listar modelos.")
        self.controller.background(lambda: self.runtime.session_command('/agy auth'),
            failed=lambda error: self.message.setText(str(error)))

    def models(self):
        if not self.save(): return
        def operation():
            self.runtime.connect_pi()
            return self.runtime.pi.request({"type": "get_available_models"}).get("data", {})
        def show(result):
            models = result.get("models", []) if isinstance(result, dict) else result
            labels = [str(m.get("provider")) + ": " + str(m.get("id")) for m in models]
            label, ok = QInputDialog.getItem(self, "Modelo del agente", "Modelos disponibles en Pi", labels, 0, False)
            if ok:
                selected = models[labels.index(label)]
                self.fields["agent_provider"].setText(selected["provider"]); self.fields["agent_model"].setText(selected["id"])
        self.controller.background(operation, show)

    def download_wake(self):
        self.message.setText("Descargando modelo local de activación…")
        def operation():
            if getattr(self.runtime, "is_remote", False): return self.runtime.request("models/wake/download", {}, timeout=180)["path"]
            from .downloads import download_wake
            return download_wake(self.runtime.storage.root)
        def done(path):
            self.fields["wake_model"].setText(path); self.message.setText("Modelo descargado. Activa la escucha local y guarda los ajustes.")
        self.controller.background(operation, done)

    def detect_voice_models(self):
        from .models import discover_voice_models
        models = discover_voice_models(roots=[Path(r"D:\Transcripcion con ia\whisper_models"), Path.home() / ".cache/huggingface/hub", self.runtime.storage.root / "models"])
        if not models:
            self.message.setText("No se encontraron modelos locales. Selecciona una carpeta o instala el ZIP de voz."); return
        labels = [item["engine"] + " · " + item["path"] for item in models]
        label, ok = QInputDialog.getItem(self, "Tus modelos de voz", "Elegir modelo existente", labels, 0, False)
        if ok:
            selected = models[labels.index(label)]
            self.fields["local_stt_engine"].setCurrentText(selected["engine"])
            self.fields["local_stt_model"].setText(selected["path"])
            self.fields["voice_provider"].setCurrentText("local")
            if selected["engine"] == "vosk": self.fields["wake_model"].setText(selected["path"])
            self.message.setText("Modelo seleccionado. Guarda los ajustes para usarlo.")

    def install_voice_pack(self):
        filename = QFileDialog.getOpenFileName(self, "Instalar modelos de voz", filter="ZIP (*.zip)")[0]
        if not filename: return
        from .downloads import install_voice_pack
        self.controller.background(lambda: install_voice_pack(filename, self.runtime.storage.root), lambda path: self.fields["wake_model"].setText(path))

    def setup_desktop_tools(self, selected=None):
        if not self.save(): return
        self.message.setText('Descargando y configurando '+', '.join(selected or ['Forge', 'ScreenView', 'InputControl'])+'…')
        self.setEnabled(False)
        def complete(result):
            self.setEnabled(True)
            self.controller.settings_window=None; self.hide()
            self.controller.show_settings()
            self.controller.settings_window.message.setText('Herramientas configuradas: '+', '.join(result.get('components', {})))
        def failed(message):
            self.setEnabled(True); self.message.setText(str(message))
        def download():
            if getattr(self.runtime, 'is_remote', False):
                return self.runtime.request('tools/setup-desktop', {'components':selected}, timeout=2400)
            from .tool_setup import setup_desktop_tools
            return setup_desktop_tools(self.runtime, selected)
        self.controller.background(download, complete, failed)

    def download_models(self, selected):
        if not self.save(): return
        self.message.setText('Descargando y verificando '+', '.join(selected)+'… Esto puede tardar varios minutos.')
        self.setEnabled(False)
        def complete(result):
            self.setEnabled(True)
            self.controller.settings_window=None; self.hide()
            self.controller.show_settings()
            self.controller.settings_window.message.setText("Modelos descargados y configurados: "+", ".join(result["installed"]))
        def failed(message):
            self.setEnabled(True); self.message.setText('No se completó la instalación: '+str(message))
        def download():
            if getattr(self.runtime, 'is_remote', False):
                return self.runtime.request('models/download', {'components':selected}, timeout=14400)
            from .model_setup import install_models
            return install_models(self.runtime, selected)
        self.controller.background(download, complete, failed)

    def detect_agent(self):
        if self.fields['engine_mode'].currentData() == 'bundled' and self.runtime.storage.config.get('owned_engine_root'):
            self.message.setText('ARISE usa su motor integrado. Configurar / reparar verifica el paquete; no busca instalaciones globales.')
            return
        from .discovery import detect
        selection = dict(self.runtime.storage.config)
        external = self.fields['engine_mode'].currentData() == 'external'
        if external and selection.get('owned_engine_root'):
            for key in ('gentle_agent_home', 'gentle_path', 'gentle_bundle_root'):
                selection[key] = ''
            selection['pi_command'] = ['pi']
        found = detect(selection)
        if found.get("gentle_agent_home"):
            self.runtime.settings({**{key: found[key] for key in ("pi_command", "gentle_path", "gentle_agent_home", "gentle_channel", "gentle_bundle_root")}, "engine_mode": "external" if external else "bundled"})
        if found["pi_command"]: self.fields["pi_command"].setText(json.dumps(found["pi_command"]))
        if found["gentle_path"]: self.fields["gentle_path"].setText(found["gentle_path"])
        self.message.setText("Pi: " + ("detectado" if found["pi_command"] else "no encontrado") + " · Gentle Shell: " + ("detectado" if found["gentle_path"] or found["gentle_installed_package"] else "no encontrado"))

    def import_tools(self):
        from .discovery import import_mcp
        filename = QFileDialog.getOpenFileName(self, "Importar MCP", filter="JSON (*.json)")[0]
        if not filename: return
        try:
            value = import_mcp(filename)
            self.fields["extra_mcp"].setText(json.dumps(value, ensure_ascii=False))
            self.message.setText("Configuración importada. Revisa los comandos antes de guardar.")
        except Exception as error: self.message.setText(str(error))

    def gmail_connect(self):
        if self.save(): self.controller.background(self.runtime.gmail.connect)

    def connect_tools(self):
        if not self.save(): return
        def operation():
            results = []
            for name, spec in self.runtime.storage.config["mcp"].items():
                if spec.get("enabled"):
                    try: results.append(f"{name}: {len(self.runtime.connect_mcp(name).tools)} herramientas")
                    except Exception as error: results.append(f"{name}: {error}")
            return "\n".join(results)
        self.controller.background(operation, lambda text: self.message.setText(text))

    @staticmethod
    def autostart_enabled():
        if os.name != "nt": return False
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
                return bool(winreg.QueryValueEx(key, "ARISE")[0])
        except OSError: return False

    @staticmethod
    def set_autostart(enabled):
        if os.name != "nt" or not getattr(sys, "frozen", False): return
        import winreg
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
            if enabled: winreg.SetValueEx(key, "ARISE", 0, winreg.REG_SZ, '"' + sys.executable + '" --background')
            else:
                try: winreg.DeleteValue(key, "ARISE")
                except FileNotFoundError: pass

    def show_capabilities(self):
        def operation():
            self.runtime.connect_pi()
            return self.runtime.status()["capabilities"]
        def done(cap):
            text = ("Carpeta: " + cap["workspace"] + "\nEjecución local autorizada: "
                    + ("Sí" if cap["local_execution_authorized"] else "No")
                    + "\nGentle verificado: " + ("Sí" if cap["gentle_verified"] else "No")
                    + "\nWord: crear y leer DOCX dentro de la carpeta.\nHerramientas Pi observadas: "
                    + (", ".join(cap["pi_tools_observed"]) or "Sin catálogo verificado")
                    + "\n\n" + cap["shell_scope"])
            QMessageBox.information(self, "Capacidades del chat", text)
        self.controller.background(operation, done)

class Panel(QWidget):
    def __init__(self, controller):
        super().__init__(); self.controller = controller; self.runtime = controller.runtime
        self.setWindowTitle(application_name()); self.setWindowIcon(icon()); self.resize(420, 680); self.setMinimumSize(320, 400); self.setMaximumWidth(900); self.setStyleSheet(STYLE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 10); layout.setSpacing(7)
        title = QLabel(application_name()); title.setObjectName("chatTitle"); title.hide()
        self.status = QLabel("Listo para ayudarte"); self.status.setObjectName("chatStatus"); self.status.hide()
        self.privacy = QLabel("Micrófono apagado · Pantalla apagada · Control apagado"); self.privacy.setObjectName("chatPrivacy"); self.privacy.setWordWrap(True); self.privacy.hide()
        from .chat_content import ChatHistory
        self.emergency=QPushButton('■ Detener')
        self.emergency.setAccessibleName('Detener manos y ojos')
        self.emergency.setToolTip('Detener manos y ojos · Ctrl+Alt+Esc')
        self.emergency.setFixedWidth(98);self.emergency.setMinimumHeight(36)
        self.emergency.clicked.connect(controller.stop)
        self.emergency.setStyleSheet('background:#6B2636;color:white;font-weight:600;padding:5px;')
        self.last_submission=None
        self.recover_shortcut=QShortcut(QKeySequence('Alt+Q'),self)
        self.recover_shortcut.setContext(Qt.WindowShortcut)
        self.recover_shortcut.activated.connect(self.restore_draft)
        from .activity_widget import ActivityWidget
        self.activity_view=ActivityWidget()
        activity_row=QHBoxLayout();activity_row.setSpacing(6)
        activity_row.addWidget(self.activity_view,1)
        activity_row.addWidget(self.emergency,0,Qt.AlignTop)
        layout.addLayout(activity_row)
        self.history = ChatHistory(); self.history.setObjectName("chatHistory"); self.history.setOpenExternalLinks(False); layout.addWidget(self.history, 1)
        self.attachments=[]
        self.attachment_bar=QWidget(); self.attachment_layout=QHBoxLayout(self.attachment_bar)
        self.attachment_layout.setContentsMargins(0,0,0,0);layout.addWidget(self.attachment_bar);self.attachment_bar.hide()
        self.history.anchorClicked.connect(self.open_link)
        self.input = ChatInput(); self.input.setAcceptRichText(False); self.input.setPlaceholderText("Escribe o pega una imagen con Ctrl+V…"); self.input.setFixedHeight(58)
        self.input.setToolTip("Enter para enviar · Shift+Enter para otra línea · Alt+Q recupera el último mensaje"); self.input.submitted.connect(self.send); self.input.image_pasted.connect(self.add_image); layout.addWidget(self.input)
        self.dictation_label = QLabel(); self.dictation_label.setWordWrap(True); self.dictation_label.hide(); layout.addWidget(self.dictation_label)
        self.study_bar = QWidget(); study_row = QHBoxLayout(self.study_bar); study_row.setContentsMargins(0,0,0,0)
        self.study_status = QLabel(); self.study_status.setWordWrap(True); study_row.addWidget(self.study_status,1)
        for label, action in [('Pausar','pause'),('Reanudar','resume'),('Finalizar','end')]:
            button = QPushButton(label); button.clicked.connect(lambda checked=False,a=action: controller.background(lambda:self.runtime.study_control(a)))
            study_row.addWidget(button)
        layout.addWidget(self.study_bar); self.study_bar.hide()
        self.connection_notice = ConnectionNotice(); layout.addWidget(self.connection_notice)
        row = QHBoxLayout(); row.setSpacing(3); layout.addLayout(row)
        self.navigation = self.icon_button(row, "menu", "Proyectos, chats y comandos")
        self.navigation_menu = QMenu(self.navigation)
        picker = QWidget(); pick_layout = QFormLayout(picker); pick_layout.setContentsMargins(10, 8, 10, 8)
        self.projects = WheelSafeCombo(); self.projects.currentIndexChanged.connect(self.select_project); pick_layout.addRow("Proyecto", self.projects)
        self.conversations = WheelSafeCombo(); self.conversations.currentIndexChanged.connect(self.select_conversation); pick_layout.addRow("Chat", self.conversations)
        action = QWidgetAction(self.navigation_menu); action.setDefaultWidget(picker); self.navigation_menu.addAction(action)
        self.navigation_menu.addAction(control_icon("plus"), "Nuevo chat", self.new_conversation)
        self.navigation_menu.addAction(control_icon("folder"), "Elegir carpeta…", self.open_project)
        self.navigation_menu.addAction("Cerrar sesión del chat (conservar historial)", lambda: controller.background(lambda:(controller.voice.end_session(), self.runtime.suspend_chat())))
        self.navigation_menu.addAction("Recuperar último mensaje · Alt+Q", self.restore_draft)
        self.navigation_menu.addAction("Configurar todo desde ZIP…", controller.install_model_pack)
        self.navigation_menu.addAction("Modo estudio / cuestionario…", controller.show_study)
        self.navigation_menu.addAction("Historial de dictado y descargas…", self.show_dictation_history)
        self.navigation_menu.addAction("Reparar dictado local Parakeet…", lambda: controller.start_dictation(repair=True) if not controller.dictation.active else None)
        self.navigation_menu.addAction(control_icon("settings"), "Ajustes…", controller.show_settings)
        self.command_dialog = None
        self.navigation_menu.addAction("Buscar comandos de la sesión…", self.refresh_commands)
        self.control = QCheckBox("Permitir control del PC"); self.control.toggled.connect(self.toggle_control)
        permission = QWidgetAction(self.navigation_menu); permission.setDefaultWidget(self.control); self.navigation_menu.addAction(permission)
        self.navigation.setMenu(self.navigation_menu)
        self.folder_button = self.icon_button(row, "folder", "Elegir carpeta del proyecto", self.open_project)
        self.icon_button(row, "plus", "Adjuntar imagen", self.choose_image)
        self.icon_button(row, "settings", "Ajustes", controller.show_settings)
        self.mic_button = self.icon_button(row, "mic", "Dictar al borrador · Parakeet · micrófono predeterminado", self.toggle_voice)
        self.mic_button.setCheckable(True)
        row.addStretch(1)
        self.icon_button(row, "stop", "Detener voz y tarea", controller.stop)
        self.send_button = self.icon_button(row, "send", "Enviar · Enter", self.send)
        self.voice_button = self.icon_button(row, "wave", "Iniciar conversación de voz", controller.wake)
        self.end_voice_button = self.icon_button(row, "stop", "Terminar conversación de voz · silenciar micrófono", controller.end_voice)
        self.end_voice_button.setObjectName('endVoiceButton')
        self.voice_button.setStyleSheet("background:#126BCA; border-radius:17px;")
        self.cancel_dictation = QShortcut(QKeySequence('Escape'), self)
        self.cancel_dictation.activated.connect(controller.cancel_dictation)
        self.reload()

    @staticmethod
    def icon_button(row, name, label, callback=None):
        button = QPushButton(); button.setObjectName("iconButton"); button.setIcon(control_icon(name)); button.setIconSize(QSize(20, 20))
        button.setFixedSize(34, 34); button.setToolTip(label); button.setAccessibleName(label)
        if callback: button.clicked.connect(lambda checked=False: callback())
        row.addWidget(button); return button

    def show_dictation_history(self):
        dialog = QDialog(self); dialog.setWindowTitle("Dictado · descargas y diagnóstico")
        layout = QVBoxLayout(dialog)
        view = QPlainTextEdit(); view.setReadOnly(True)
        view.setPlainText(self.controller.dictation.history_text()); layout.addWidget(view)
        close = QPushButton("Cerrar"); close.clicked.connect(dialog.accept); layout.addWidget(close)
        dialog.resize(580, 420); dialog.exec()

    def toggle_voice(self):
        if self.controller.dictation.state == 'recording':
            self.controller.dictation.stop()
        elif self.controller.dictation.active:
            self.controller.cancel_dictation()
        elif not self.input.isReadOnly():
            self.controller.start_dictation()
        else:
            self.mic_button.setChecked(False)

    def dictation_state(self, state):
        labels = {'idle': 'Dictar al borrador · Parakeet · micrófono predeterminado',
                  'starting': 'Preparando micrófono… · clic para cancelar',
                  'installing': 'Preparando Parakeet local (unos 670 MB)… · clic para cancelar',
                  'recording': 'Escuchando… · pulsa el micrófono ↑ para transcribir',
                  'transcribing': 'Transcribiendo en el PC… · clic para cancelar',
                  'cancelling': 'Cancelando dictado…', 'restoring': 'Cerrando micrófono…'}
        label = labels[state]
        self.mic_button.setIcon(control_icon('mic-up' if state == 'recording' else 'mic'))
        self.mic_button.setChecked(state == 'recording')
        self.mic_button.setToolTip(label); self.mic_button.setAccessibleName(label)
        self.dictation_label.setText(label); self.dictation_label.setVisible(state != 'idle')
        self.voice_button.setEnabled(state == "idle")
        self.controller.last_interaction = time.monotonic()

    def insert_dictation(self, chat, text):
        if chat != self.current_chat or self.input.isReadOnly() or not text:
            return
        cursor = self.input.textCursor()
        # Preserve text typed during recognition; never replace the whole draft.
        before = self.input.toPlainText()[:cursor.position()]
        cursor.clearSelection()
        cursor.beginEditBlock()
        cursor.insertText((' ' if before and not before[-1].isspace() else '') + text)
        cursor.endEditBlock(); self.input.setTextCursor(cursor); self.input.setFocus()
        self.connection_notice.set_notice('Dictado listo. Revisa el texto y pulsa Enviar.')

    def open_link(self, url):
        if url.scheme() in ('https','http'):
            if QMessageBox.question(self,'Abrir enlace',url.toString()) == QMessageBox.Yes:
                QDesktopServices.openUrl(url)

    def choose_image(self):
        path,_=QFileDialog.getOpenFileName(self,'Adjuntar imagen',filter='Imágenes (*.png *.jpg *.jpeg *.webp)')
        if path:
            image=QImage(path)
            if image.isNull(): QMessageBox.warning(self,'Imagen','No se pudo abrir la imagen.')
            else: self.add_image(image)

    def add_image(self, image):
        if self.input.isReadOnly(): return
        from .attachments import MAX_IMAGES, MAX_IMAGE_BYTES
        if len(self.attachments)>=MAX_IMAGES:
            QMessageBox.warning(self,'Imágenes','Puedes adjuntar hasta cuatro imágenes.');return
        image=image.scaled(1600,1600,Qt.KeepAspectRatio,Qt.SmoothTransformation)
        buffer=QBuffer();buffer.open(QIODevice.WriteOnly);image.save(buffer,'PNG')
        raw=bytes(buffer.data())
        if len(raw)>MAX_IMAGE_BYTES:
            QMessageBox.warning(self,'Imagen','La imagen supera 2 MB. Recórtala o reduce su tamaño.');return
        self.attachments.append({'type':'image','mimeType':'image/png','data':base64.b64encode(raw).decode()})
        self.refresh_attachments()

    def refresh_attachments(self):
        while self.attachment_layout.count():
            item=self.attachment_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        for index,item in enumerate(self.attachments):
            button=QPushButton();button.setIcon(QIcon(QPixmap.fromImage(QImage.fromData(base64.b64decode(item['data'])))))
            button.setIconSize(QSize(64,48));button.setFixedSize(100,66);button.setText('×');button.setToolTip('Quitar imagen '+str(index+1))
            button.setAccessibleName('Quitar imagen '+str(index+1))
            button.clicked.connect(lambda checked=False,i=index:self.remove_image(i))
            self.attachment_layout.addWidget(button)
        self.attachment_layout.addStretch(1)
        self.attachment_bar.setVisible(bool(self.attachments))

    def remove_image(self,index):
        self.attachments.pop(index);self.refresh_attachments()

    def append(self, role, text, images=None):
        self.history.append_message(role,text,images)

    def reload(self):
        self.controller.cancel_dictation()
        if getattr(self, 'command_dialog', None):
            self.command_dialog.close()
            self.command_dialog = None
        catalog = self.runtime.project_catalog(); self.current_chat = catalog["active"]["conversation"]
        self.history.clear()
        self.connection_notice.set_notice('')
        snapshot = self.runtime.status()
        self.activity_view.set_activity(snapshot.get("activity", {}))
        if hasattr(self,"study_bar"): self.study_bar.setVisible(bool(snapshot.get("study",{}).get("active")))
        for message in self.runtime.storage.messages(self.current_chat):
            if message["role"] == "system": continue  # Retain diagnostic records without replaying notices as answers.
            self.append({"user":"Tú","voice_user":"Voz · Tú","voice_assistant":"Voz · ARISE"}.get(message["role"],"ARISE"), message["text"], message.get("images"))
        self.conversations.blockSignals(True); self.conversations.clear()
        for c in catalog["chats"]: self.conversations.addItem(c["title"], c["id"])
        self.conversations.setCurrentIndex(max(0, self.conversations.findData(self.current_chat))); self.conversations.blockSignals(False)
        self.projects.blockSignals(True); self.projects.clear()
        for p in catalog["projects"]: self.projects.addItem(p["name"], p["path"])
        active_project = next(p for p in catalog["projects"] if p["id"] == catalog["active"]["project"])
        self.projects.setCurrentIndex(self.projects.findData(active_project["path"])); self.projects.blockSignals(False)
        self.projects.setToolTip(catalog["active"]["workspace"])
        self.folder_button.setToolTip("Carpeta: " + catalog["active"]["workspace"])
        self.navigation.setToolTip(active_project["name"] + " · " + self.conversations.currentText())

    def refresh_commands(self):
        from .command_picker import CommandPicker
        if self.command_dialog:
            self.command_dialog.close()
        chat = self.current_chat
        def selected(command):
            if self.current_chat == chat and self.command_dialog is dialog:
                self.run_command(command)
        dialog = CommandPicker(self, selected)
        self.command_dialog = dialog
        dialog.show()
        def operation():
            self.runtime.connect_pi()
            return self.runtime.pi.request({"type":"get_commands"}).get("data", {}).get("commands", [])
        def done(commands):
            if chat == self.current_chat and self.command_dialog is dialog and dialog.isVisible():
                dialog.set_commands(commands)
        def failed(_):
            if self.command_dialog is dialog and dialog.isVisible():
                dialog.status.setText("No se pudieron cargar los comandos. Cierra y vuelve a abrir para reintentar.")
        self.controller.background(operation, done, failed=failed)

    def run_command(self, text):
        if text == "/gentle:customize":
            self.controller.show_settings(); return
        self.controller.background(lambda:self.runtime.session_command(text))

    def open_project(self):
        path = QFileDialog.getExistingDirectory(self, "Elegir carpeta del proyecto")
        if path:
            self.controller.voice.end_session()
            self.controller.background(lambda: self.runtime.select_project(path), lambda _: self.reload())

    def select_project(self):
        path = self.projects.currentData()
        if path:
            self.controller.voice.end_session()
            self.controller.background(lambda: self.runtime.select_project(path), lambda _: self.reload())

    def restore_draft(self):
        if not self.last_submission:return
        chat,text,images=self.last_submission
        if chat!=self.current_chat or self.input.toPlainText().strip() or self.attachments:
            self.status.setText('El borrador actual se conserva.');return
        self.input.setPlainText(text);self.attachments=list(images);self.refresh_attachments();self.input.setFocus()
        self.status.setText('Borrador recuperado; no se ha reenviado.')

    def send(self):
        if self.controller.dictation.active: return
        text=self.input.toPlainText().strip();images=list(self.attachments)
        if self.input.isReadOnly() or (not text and not images):return
        if text.startswith('/'):
            if images:
                QMessageBox.warning(self,'Imágenes','Envía las imágenes con un mensaje, sin comando /.');return
            self.input.clear();self.run_command(text);return
        self.last_submission=(self.current_chat,text,images)
        self.send_button.setEnabled(False);self.input.setReadOnly(True)
        def done(_):
            self.input.clear();self.attachments.clear();self.refresh_attachments()
            self.send_button.setEnabled(True);self.input.setReadOnly(False);self.input.setFocus()
        def failed(_):
            self.send_button.setEnabled(True);self.input.setReadOnly(False)
        self.controller.background(lambda:self.runtime.steer(text,images) if images else self.runtime.steer(text),done,failed)

    def select_conversation(self):
        identity = self.conversations.currentData()
        if not identity or identity == self.runtime.conversation: return
        self.controller.voice.end_session()
        self.controller.background(lambda: self.runtime.switch_conversation(identity), lambda _: self.reload())

    def new_conversation(self):
        self.controller.voice.end_session()
        self.controller.background(lambda: self.runtime.switch_conversation(), lambda _: self.reload())

    def toggle_control(self, enabled):
        self.controller.background(lambda: self.runtime.set_desktop(enabled))

class Controller(QObject):
    wake_requested = Signal(str)
    stop_requested = Signal()
    def __init__(self, app, runtime, orb, start_voice=True):
        super().__init__(); self.app, self.runtime, self.orb = app, runtime, orb
        self.voice = runtime.voice_service if getattr(runtime, "is_remote", False) else VoiceService(runtime); self.workers = []; self.cursor = 0; self.closed = False
        self.settings_window = None; self.pending_dialogs = {}
        from .dictation import Dictation
        self.dictation = Dictation(runtime.storage.root, self)
        self.dictation_attempt = 0; self.dictation_restore_mute = None; self.dictation_preparing = False
        self.panel = Panel(self)
        self.dictation.state_changed.connect(self.panel.dictation_state)
        self.dictation.message.connect(self.panel.connection_notice.set_notice)
        self.dictation.transcript.connect(self.panel.insert_dictation)
        self.dictation.finished.connect(self.restore_dictation_voice)
        self.wake_requested.connect(self._wake); self.stop_requested.connect(self._stop)
        self.orb.setToolTip("ARISE · clic para abrir el chat · clic derecho para detener")
        self.orb.setAccessibleName("ARISE: abrir conversación")
        self.tray = QSystemTrayIcon(icon(), self); self.tray.setToolTip("ARISE · Oye Arise")
        self.menu = QMenu()
        for label, callback in (("Hablar", self.wake), ("Conversación", self.show_panel), ("Ajustes", self.show_settings),
                                ("Silenciar / activar micrófono", self.toggle_mute), ("Detener manos y ojos · Ctrl+Alt+Esc", self.stop), ("Reiniciar asistente", self.restart), ("Salir de ARISE", self.quit_all), ("Ocultar conversación", self.hide_panel), ("Buscar actualizaciones", self.check_updates)):
            self.menu.addAction(label, callback)
        self.tray.setContextMenu(self.menu); self.tray.activated.connect(lambda reason: self.show_panel() if reason == QSystemTrayIcon.Trigger else None)
        if QSystemTrayIcon.isSystemTrayAvailable(): self.tray.show()
        self.layout_pending = set(); self.layout_docked = False
        self.press_point = None; self.double_click = False
        self.last_interaction = time.monotonic()
        self.idle_timer = QTimer(self); self.idle_timer.setInterval(1000); self.idle_timer.timeout.connect(self.hide_if_idle); self.idle_timer.start()
        self.position_timer = QTimer(self); self.position_timer.setSingleShot(True); self.position_timer.setInterval(250); self.position_timer.timeout.connect(self.save_position)
        app.installEventFilter(self)
        self.timer = QTimer(self); self.timer.timeout.connect(self.poll); self.timer.start(80)
        self.hotkeys = Hotkeys(self.wake, self.stop)
        if os.name == "nt" and not getattr(runtime, "is_remote", False) and not self.hotkeys.start(): self.runtime.emit("notice", {"text": "Algún atajo está ocupado; usa el orbe o la bandeja."})
        app.aboutToQuit.connect(self.close)
        if start_voice: self.voice.start()
        self.reconfigure()
        self.update_busy = False
        if start_voice and getattr(sys, "frozen", False) and not os.getenv("ARISE_SKIP_NETWORK_SETUP"): QTimer.singleShot(1500, self.check_updates)

    def install_gentle_native(self):
        if self.runtime.storage.config.get('engine_mode','bundled') == 'bundled':
            self.install_gentle(); return
        if getattr(self, 'gentle_busy', False): return
        answer=QMessageBox.question(None, "Instalación nativa de Gentle", "Esta alternativa abre la TUI oficial en otra consola. Conserva el motor actual de ARISE: la conexión del entorno nativo con ARISE todavía no está habilitada.\n\n¿Probar la instalación independiente?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes: return
        choice, accepted=QInputDialog.getItem(None, "Gentle AI", "Binario para abrir la TUI", ["Binario integrado (verificado)", "Elegir gentle-ai.exe"], 0, False)
        if not accepted: return
        binary=None
        if choice == "Elegir gentle-ai.exe":
            binary, _=QFileDialog.getOpenFileName(None, "Selecciona gentle-ai.exe estable 4.3.1+", "", "Gentle AI (*.exe)")
            if not binary: return
        self.gentle_busy=True
        def operation():
            if getattr(self.runtime, 'is_remote', False):
                return self.runtime.request('gentle/install-native', {'binary':binary or None}, timeout=4600)
            from .gentle_native_setup import install_native_tui
            return install_native_tui(self.runtime, binary or None)
        def done(result): self.gentle_busy=False; self.show_panel()
        def failed(message): self.gentle_busy=False
        self.background(operation, done, failed)

    def update_dependencies(self, include_gentle=False):
        if getattr(self,'gentle_busy',False): return
        message=('Se descargará de nuevo Engram estable y se verificará su checksum. ARISE usará su ruta explícita sin borrar memorias. '
                 'La comprobación del proveedor activo se hace después con mem_doctor.')
        if include_gentle:
            message+=' Primero se abrirá el instalador oficial de Gentle: elige estable y revisa el plan de actualización de Shell, Pi y sus componentes.'
        if QMessageBox.question(None,'Actualizar dependencias de ARISE',message,QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes: return
        self.gentle_busy=True
        def operation():
            remote=getattr(self.runtime,'is_remote',False)
            if include_gentle:
                if remote: self.runtime.request('gentle/update',{},timeout=3700)
                else:
                    from .gentle_setup import install_gentle
                    install_gentle(self.runtime,force_update=True)
            if remote: return self.runtime.request('engram/update',{},timeout=300)
            from .engram_setup import update_engram
            return update_engram(self.runtime)
        def done(result):
            self.gentle_busy=False
            if getattr(self.runtime,'is_remote',False): self.runtime.storage.config=self.runtime.request('config')
            if self.settings_window:
                for key in ('engram_bin','pi_command','gentle_path'):
                    value=self.runtime.storage.config.get(key,'')
                    self.settings_window.fields[key].setText(json.dumps(value) if key=='pi_command' else value)
            self.show_panel()
        def failed(message):
            self.gentle_busy=False
            self.show_panel()
        self.background(operation,done,failed)

    def install_gentle(self):
        if getattr(self,'gentle_busy',False): return
        self.gentle_busy=True
        def operation():
            if getattr(self.runtime,'is_remote',False):
                return self.runtime.request('gentle/install',{},timeout=3700)
            from .gentle_setup import install_gentle
            return install_gentle(self.runtime)
        def done(result):
            self.gentle_busy=False
            if getattr(self.runtime,'is_remote',False): self.runtime.storage.config=self.runtime.request('config')
            self.reconfigure();self.show_panel()
        def failed(message): self.gentle_busy=False
        self.background(operation,done,failed)

    def install_model_pack(self, filename=None):
        if getattr(self,'pack_busy',False): return
        if not isinstance(filename,str) or not filename:
            filename=QFileDialog.getOpenFileName(self.panel,"Configurar ARISE desde ZIP",filter="Paquete ARISE (*.zip)")[0]
        if not filename: return
        self.pack_busy=True
        self.show_panel()
        def operation():
            if getattr(self.runtime,'is_remote',False):
                return self.runtime.request('models/offline/install',{'path':filename},timeout=900)
            from .offline_pack import install_offline_pack
            return install_offline_pack(self.runtime,filename)
        def done(result):
            self.pack_busy=False
            if getattr(self.runtime,'is_remote',False): self.runtime.storage.config=self.runtime.request('config')
            if self.settings_window:
                self.settings_window.close();self.settings_window=None
            self.reconfigure();self.show_panel()
            from .discovery import command_available, gentle_valid
            config=self.runtime.storage.config
            if not (config.get("gentle_agent_home") and gentle_valid(config.get("gentle_path", "")) and command_available(config.get("pi_command"))):
                self.install_gentle()
        def failed(message): self.pack_busy=False
        self.background(operation,done,failed)

    def background(self, operation, complete=None, failed=None):
        worker = Worker(self); self.workers.append(worker)
        worker.finished.connect(lambda result: complete(result) if complete else None)
        def report_error(text):
            try: self.runtime.emit("error", {"text": text})
            except RuntimeError: self.panel.status.setText(text)
        worker.failed.connect(report_error)
        if failed: worker.failed.connect(failed)
        def cleanup(*_):
            if worker in self.workers: self.workers.remove(worker)
            worker.deleteLater()
        worker.finished.connect(cleanup); worker.failed.connect(cleanup); worker.start(operation)

    def start_dictation(self, repair=False):
        if self.dictation.active: return
        self.dictation_preparing = True
        self.dictation_attempt += 1
        attempt = self.dictation_attempt
        chat = self.panel.current_chat
        self.dictation.set_state('starting')
        def prepare():
            muted = self.voice.muted
            self.voice.end_session(); self.voice.mute(True)
            if self.closed: self.voice.mute(muted)
            return muted
        def ready(muted):
            self.dictation_preparing = False
            if self.closed or attempt != self.dictation_attempt or chat != self.panel.current_chat:
                if not self.closed:
                    self.dictation_restore_mute = muted
                    self.restore_dictation_voice()
                return
            self.dictation_restore_mute = muted
            self.dictation.start(self.runtime.storage.config, chat, repair=repair)
        def failed(_):
            self.dictation_preparing = False
            self.dictation.set_state('idle')
        self.background(prepare, ready, failed)

    def restore_dictation_voice(self):
        muted = self.dictation_restore_mute
        self.dictation_restore_mute = None
        if muted is not None and not self.closed:
            self.dictation.set_state('restoring')
            self.background(lambda: self.voice.mute(muted), lambda _: self.dictation.set_state('idle'), lambda _: self.dictation.set_state('idle'))

    def cancel_dictation(self):
        self.dictation_attempt += 1
        if self.dictation_preparing:
            self.dictation.set_state('cancelling')
        elif self.dictation.state != 'restoring':
            self.dictation.cancel()

    def wake(self, initial=""):
        self.wake_requested.emit(initial if isinstance(initial, str) else "")

    def _wake(self, initial):
        if self.dictation.active: return
        self.last_interaction = time.monotonic()
        self.orb.show(); self.orb.raise_()
        if self.runtime.storage.config.get("wake_open_panel",True):self.show_panel()
        self.background(lambda:(self.voice.mute(False), self.voice.wake(initial)))

    def stop(self): self.stop_requested.emit()

    def _stop(self):
        self.cancel_dictation()
        self.close_dialogs()
        self.panel.status.setText('Deteniendo manos y ojos…')
        self.background(lambda:(self.voice.end_session(),self.runtime.stop()))

    def close_dialogs(self):
        for dialog in list(self.pending_dialogs.values()):
            dialog.setProperty("arise_cancelled", True); dialog.reject()
        self.pending_dialogs.clear()

    def toggle_mute(self): self.voice.mute(not self.voice.muted)

    def show_panel(self):
        self.last_interaction = time.monotonic(); self.anchor_panel()
        self.panel.show(); self.panel.raise_(); self.panel.activateWindow(); self.orb.raise_()

    def hide_panel(self): self.panel.hide()

    def hide_if_idle(self):
        if not self.dictation.active and self.panel.isVisible() and time.monotonic() - self.last_interaction >= 60:
            self.hide_panel()

    def anchor_panel(self):
        screen = self.app.screenAt(self.orb.geometry().center()) or self.app.primaryScreen()
        rect = screen.availableGeometry(); gap = 12
        x = self.orb.x() - self.panel.width() - gap
        if x < rect.left(): x = self.orb.x() + self.orb.width() + gap
        x = max(rect.left(), min(x, rect.right() - self.panel.width() + 1))
        y = max(rect.top(), min(self.orb.y(), rect.bottom() - self.panel.height() + 1))
        self.panel.move(x, y)

    def save_position(self):
        if self.closed or self.layout_docked: return
        self.clamp_position()
        position = [self.orb.x(), self.orb.y()]
        self.runtime.storage.config["orb_position"] = position
        self.background(lambda: self.runtime.storage.save_config({"orb_position": position}) if getattr(self.runtime, "is_remote", False) else self.runtime.storage.save_config(self.runtime.storage.config.copy()))

    def show_settings(self):
        if self.settings_window is None: self.settings_window = Settings(self)
        self.settings_window.show(); self.settings_window.raise_(); self.settings_window.activateWindow()

    def check_updates(self, checked=False):
        from .updates import check_update
        if self.update_busy: return
        self.update_busy = True
        def complete(manifest):
            self.update_busy = False
            if manifest: self.offer_update(manifest)
        def failed(message):
            self.update_busy = False
            self.tray.setToolTip("ARISE · No se pudo consultar main. Usa Buscar actualizaciones para reintentar.")
        # A network failure does not interrupt a conversation or open the hidden panel.
        worker = Worker(self); self.workers.append(worker)
        worker.finished.connect(complete); worker.failed.connect(failed)
        def cleanup(*_):
            if worker in self.workers: self.workers.remove(worker)
            worker.deleteLater()
        worker.finished.connect(cleanup); worker.failed.connect(cleanup); worker.start(lambda:self.runtime.request("updates/check",{},timeout=20).get("manifest") if getattr(self.runtime,"is_remote",False) else check_update())

    def offer_update(self, manifest):
        from . import __version__
        from .update_dialog import UpdateDialog
        box = UpdateDialog(manifest, __version__, self.orb)
        box.accepted.connect(lambda: self.download_and_install(manifest))
        self.update_dialog = box; box.open()

    def download_and_install(self, manifest):
        from .updates import download_update, launch_update
        from .bundle import application_root
        if self.update_busy: return
        self.update_busy = True; self.tray.setToolTip("ARISE · Descargando actualización…")
        self.update_progress=QProgressDialog('Conectando con GitHub…','',0,100,self.panel)
        self.update_progress.setCancelButton(None);self.update_progress.setWindowTitle('Actualizar ARISE')
        self.update_progress.setAutoClose(False);self.update_progress.setValue(0);self.update_progress.show()
        def complete(installer):
            self.update_progress.close()
            try:
                launch_update(installer, manifest, self.runtime.storage.root, application_root())
            except Exception as error: failed(str(error)); return
            self.close_dialogs()
            self.background(self.runtime.shutdown if getattr(self.runtime, "is_remote", False) else self.runtime.close, lambda _:self.quit(), lambda _:self.quit())
        def failed(message):
            self.update_busy = False; self.tray.setToolTip(application_name())
            self.update_progress.close()
            box = QMessageBox(self.orb); box.setWindowTitle("ARISE · Actualización")
            box.setTextFormat(Qt.PlainText); box.setText("No se pudo completar la descarga. Puedes reintentarlo desde Ajustes.\n\n"+message); self.update_dialog = box; box.open()
        self.background(lambda:Path(self.runtime.request("updates/download",{"manifest":manifest},timeout=7200)["path"]) if getattr(self.runtime,"is_remote",False) else download_update(manifest, self.runtime.storage.root), complete, failed)

    def change_language(self, locale):
        self.language_epoch = getattr(self,'language_epoch',0) + 1
        epoch = self.language_epoch
        if not hasattr(self,'language_lock'): self.language_lock = threading.Lock()
        self.translator.set_language(locale)
        def save():
            with self.language_lock:
                if epoch != self.language_epoch: return
                if getattr(self.runtime,'is_remote',False):
                    self.runtime.request('preferences',{'ui_language':locale})
                else:
                    self.runtime.storage.save_config({**self.runtime.storage.config,'ui_language':locale})
                self.runtime.storage.config['ui_language'] = locale
        def failed(message):
            if epoch != self.language_epoch: return
            previous = self.runtime.storage.config.get('ui_language','es')
            self.translator.set_language(previous)
            if self.settings_window:
                choice=self.settings_window.language_choice
                choice.blockSignals(True);choice.setCurrentIndex(choice.findData(previous));choice.blockSignals(False)
            self.panel.status.setText(str(message))
        self.background(save,failed=failed)

    def reconfigure(self):
        c = self.runtime.storage.config
        from .i18n import LiveTranslator
        if not hasattr(self,'translator'): self.translator = LiveTranslator(self.app,c.get('ui_language','es'))
        else: self.translator.set_language(c.get('ui_language','es'))
        self.orb.apply_state({"size": c["orb_size"], "visible": True, "reason": "OYE ARISE", "reduced_motion": c["reduced_motion"]})
        for timer in self.orb.findChildren(QTimer): timer.setInterval(200 if c["reduced_motion"] else 100 if c.get("orb_animation") == "sprite" else 33)
        self.clamp_position()

    def clamp_position(self):
        point = self.orb.pos()
        screen = self.app.screenAt(point) or self.app.primaryScreen()
        rect = screen.availableGeometry()
        self.orb.move(max(rect.left(), min(point.x(), rect.right() - self.orb.width() + 1)),
                      max(rect.top(), min(point.y(), rect.bottom() - self.orb.height() + 1)))

    def eventFilter(self, obj, event):
        if self.closed: return False
        interactive = (QEvent.MouseButtonPress, QEvent.MouseButtonDblClick, QEvent.MouseMove, QEvent.KeyPress, QEvent.Wheel, QEvent.TouchBegin)
        if event.type() in interactive and isinstance(obj, QWidget):
            if obj is self.orb or obj is self.panel or self.panel.isAncestorOf(obj) or obj.window() in (self.panel, self.settings_window) or obj in self.pending_dialogs.values():
                self.last_interaction = time.monotonic()
        if obj is self.panel and event.type() in (QEvent.Close, QEvent.Hide):
            self.panel.hide() if event.type() == QEvent.Close else None
            event.ignore() if event.type() == QEvent.Close else None
            return event.type() == QEvent.Close
        if obj is self.panel and event.type() == QEvent.Resize: self.anchor_panel()
        if obj is self.orb:
            if event.type() == QEvent.Move:
                self.anchor_panel(); self.position_timer.start()
            elif event.type() == QEvent.MouseButtonPress:
                if event.button()==Qt.RightButton:
                    self.menu.popup(event.globalPosition().toPoint());return True
                self.double_click = False
                self.press_point = event.globalPosition().toPoint()
                if event.button() == Qt.RightButton:
                    self.menu.popup(self.press_point); return True
            elif event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                moved = self.press_point and (event.globalPosition().toPoint() - self.press_point).manhattanLength() > 6
                if moved:self.layout_docked=False
                self.clamp_position()
                self.position_timer.start()
                if self.double_click: self.double_click = False
                elif not moved: self.hide_panel() if self.panel.isVisible() else self.show_panel()
            elif event.type() == QEvent.MouseButtonDblClick:
                self.double_click = True; self.show_panel(); return True
            elif event.type() == QEvent.Close:
                event.ignore(); self.hide_panel(); return True
        return super().eventFilter(obj, event)

    def desktop_layout_event(self, data):
        identifier=data.get("id")
        if data.get("action")=="prepare":
            self.layout_pending.add(identifier)
            self.hide_panel()
            if not self.layout_docked:
                screen=self.app.screenAt(self.orb.geometry().center()) or self.app.primaryScreen()
                rect=screen.availableGeometry();corner=self.runtime.storage.config.get("desktop_orb_corner","bottom-right")
                self.layout_docked=True
                x=rect.right()-self.orb.width()-12 if corner.endswith("right") else rect.left()+12
                y=rect.bottom()-self.orb.height()-12 if corner.startswith("bottom") else rect.top()+12
                self.orb.move(x,y)
            self.orb.hide()
            def acknowledge():
                if identifier not in self.layout_pending:return
                if getattr(self.runtime,"is_remote",False):
                    self.background(lambda:self.runtime.request("desktop/layout-ack",{"id":identifier}))
                else:self.runtime.desktop_layout.acknowledge(identifier)
            QTimer.singleShot(40,acknowledge)
        else:
            self.layout_pending.discard(identifier)
            if not self.layout_pending:self.orb.show()

    def poll(self):
        if not getattr(self.runtime,"is_remote",False):self.runtime.desktop_layout.heartbeat()
        try:
            result = self.runtime.events_after(self.cursor); self.cursor = result["cursor"]
        except RuntimeError:
            self.panel.status.setText("Proceso residente desconectado")
            return
        for event in result["events"]:
            kind, data = event["kind"], event["data"]
            if kind == 'shutdown_requested':
                self.quit(); return
            if kind == 'study_setup':
                self.show_study(); continue
            if kind == 'study_result':
                if event.get('conversation') == self.panel.current_chat: self.show_panel()
                continue
            if kind == 'study_status':
                if event.get('conversation') == self.panel.current_chat:
                    was_active = self.panel.study_bar.isVisible()
                    if data.get('paused') or was_active and not data.get('active'): self.show_panel()
                    self.panel.study_status.setText('Estudio pausado' if data.get('paused') else 'Estudio activo · observación periódica' if data.get('active') else '')
                    self.panel.study_bar.setVisible(bool(data.get('active')))
                continue
            if kind == "desktop_layout":
                self.desktop_layout_event(data);continue
            if kind == 'tools_configured':
                self.runtime.storage.config['mcp'].update(data['mcp'])
                if self.settings_window:
                    for name,spec in data['mcp'].items():
                        if name in self.settings_window.mcp:
                            enabled, command = self.settings_window.mcp[name]
                            enabled.setChecked(spec.get('enabled',False)); command.setText(json.dumps(spec['command']))
                continue
            if kind == "conversation_changed":
                self.close_dialogs(); self.panel.reload(); continue
            if event.get("conversation") != self.panel.current_chat: continue
            if kind == "activity":
                self.panel.activity_view.set_activity(data)
            elif kind == "orb":
                if data["state"]=="wake_detected" and self.runtime.storage.config.get("wake_open_panel",True):self.show_panel()
                active = data["state"] != "idle"
                self.orb.apply_state({"speaking": data["state"] == "speaking", "listening": data["state"] == "listening",
                    "reason": data["activity"], "state": data["state"], "privacy": data, "speaker": {"understanding": "subagent", "waiting_approval": "approval", "error": "error", "speaking": "human", "working": "working"}.get(data["state"], "orchestrator"),
                    "visible": not self.layout_pending})
                self.panel.status.setText(data["activity"])
                self.orb.setToolTip("ARISE · "+data["activity"]+" · clic para abrir chat")
                self.panel.send_button.setToolTip(data["activity"])
                if data['control']:self.panel.emergency.setText('■ Detener')
                self.panel.control.setText("Control del PC " + ("activo" if data["control"] else "apagado"))
                self.panel.privacy.setText("Micrófono " + ("activo" if data["microphone"] else "apagado") + " · Pantalla " + ("activa" if data["screen"] else "apagada") + " · Control " + ("activo" if data["control"] else "apagado"))
                self.panel.activity_view.setToolTip(data["activity"]+"\n"+self.panel.privacy.text())
                self.panel.control.blockSignals(True); self.panel.control.setChecked(data["control"]); self.panel.control.blockSignals(False)
            elif kind == 'desktop_stopped':
                if self.dictation.active: self.cancel_dictation()
                self.panel.status.setText('Manos y ojos detenidos. Reactivación manual.' if data['confirmed'] else 'No se pudo confirmar la parada: '+', '.join(data['errors']))
                self.panel.emergency.setText('✓ Detenido' if data['confirmed'] else '⚠ Revisar')
                self.panel.emergency.setToolTip(self.panel.status.text()+' · Ctrl+Alt+Esc')
            elif kind == 'update_progress' and getattr(self,'update_progress',None):
                received=data['received'];total=data['total']
                self.update_progress.setValue(int(100*received/total))
                self.update_progress.setLabelText(f"Descargando: {received/1048576:.1f} de {total/1048576:.1f} MB")
            elif kind == "notice":
                self.panel.connection_notice.set_notice(data.get("text", ""))
            elif kind in ("user", "assistant_end", "error"):
                if kind=='error':
                    from .user_errors import friendly_error
                    data={**data,'text':friendly_error(data.get('text',''))}
                    self.panel.input.setToolTip("Alt+Q: recuperar último mensaje para revisarlo; no se reenvía automáticamente.")
                self.panel.append({"user": "Tú", "assistant_end": "ARISE", "notice": "Aviso", "error": "Revisar"}[kind], data.get("text", ""), data.get("images"))
                if kind == "error":
                    self.runtime.orb.update("error")
                    self.tray.setToolTip('ARISE · '+data.get('text','Revisar aviso')[:200])
            elif kind == "voice_transcript":
                if data['role']=='user': self.last_interaction=time.monotonic()
                self.panel.append("Voz · " + data["role"], data["text"])
            elif kind == "input_text": self.panel.input.setPlainText(data["text"]); self.panel.input.setFocus()
            elif kind == "approval": self.approval(data)
            elif kind == "dialog":
                if data.get('terminal_id') or not (self.runtime.storage.config['voice_provider']=='local' and self.voice.active.is_set()): self.dialog(data)
            elif kind == "dialog_resolved":
                dialog=self.pending_dialogs.pop(data['id'],None)
                if dialog: dialog.setProperty('arise_cancelled',True); dialog.reject()

    def approval(self, data):
        # Nonmodal: stop hotkey, cancellation and microphone state keep updating.
        from .task_dialog import TaskDialog
        preview = data.get('preview', '')
        if not isinstance(preview, str): preview = json.dumps(preview, ensure_ascii=False, indent=2)
        box = TaskDialog({'method':'confirm', 'title':data.get('action','ARISE · Revisar'), 'message':preview}, self.panel)
        box.finished.connect(lambda result: self.answer_approval(data['id'], result == QDialog.Accepted))
        box.finished.connect(box.deleteLater)
        self.show_panel(); box.open()

    def answer_approval(self, identity, approved):
        try: self.runtime.approve(identity, approved)
        except ValueError: pass

    def dialog(self, data):
        origin = self.panel.current_chat
        def submit(dialog, result, value, confirmed=False):
            if dialog.property("arise_cancelled") or origin != self.panel.current_chat: return
            record={"id":data["id"],"cancelled":result != QDialog.Accepted,"value":value,"confirmed":confirmed}
            self.background(lambda:self.runtime.answer_dialog(record))
        def track(dialog):
            self.pending_dialogs[data["id"]] = dialog
            dialog.finished.connect(lambda _:self.pending_dialogs.pop(data["id"],None))
            dialog.finished.connect(dialog.deleteLater)
            if data.get("timeoutMs"):
                timer=QTimer(dialog); timer.setSingleShot(True); timer.timeout.connect(dialog.reject); timer.start(max(1,int(data["timeoutMs"])))
            dialog.open()
        from .task_dialog import TaskDialog
        dialog = TaskDialog(data, self.panel)
        dialog.finished.connect(lambda result: submit(
            dialog, result, dialog.value(), data['method'] == 'confirm' and result == QDialog.Accepted))
        track(dialog)

    def open_pi(self):
        # Retained for older menu callers; authentication always stays in the panel.
        from .accounts_widget import AccountsDialog
        AccountsDialog(self.runtime, self.panel).exec()

    def open_data(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.runtime.storage.root)))

    def restart(self):
        if not getattr(self.runtime, "is_remote", False):
            self.runtime.emit("notice", {"text": "La vista de prueba no ejecuta un proceso residente."}); return
        root = self.runtime.storage.root
        def operation():
            from .daemon import read_descriptor, ping, ensure_daemon
            try: self.runtime.shutdown()
            except RuntimeError: pass
            deadline = time.monotonic() + 8
            while ping(read_descriptor(root)) and time.monotonic() < deadline: time.sleep(.1)
            return ensure_daemon(root)
        def complete(descriptor):
            from .remote import RemoteAssistant
            self.runtime = RemoteAssistant(descriptor, root); self.voice = self.runtime.voice_service
            self.panel.runtime = self.runtime; self.cursor = 0
            if self.settings_window: self.settings_window.close(); self.settings_window.deleteLater(); self.settings_window = None
            self.panel.reload(); self.reconfigure()
        self.background(operation, complete)

    def end_voice(self):
        self.cancel_dictation()
        self.background(lambda: self.voice.mute(True))

    def show_study(self):
        from .study_widget import StudyDialog
        dialog = StudyDialog(self, self.panel)
        dialog.exec()

    def quit_all(self):
        if getattr(self.runtime, "is_remote", False):
            self.background(self.runtime.shutdown, lambda _: self.quit(), lambda _: self.quit())
        else: self.quit()

    def quit(self):
        self.app.removeEventFilter(self)
        self.app.quit()

    def close(self):
        if self.closed: return
        muted = self.dictation_restore_mute
        self.closed = True; self.dictation.close()
        if hasattr(self,"translator"): self.translator.close()
        if muted is not None:
            try: self.voice.mute(muted)
            except RuntimeError: pass
        self.app.removeEventFilter(self); self.timer.stop(); self.idle_timer.stop(); self.position_timer.stop(); self.hotkeys.close(); self.voice.close(); self.runtime.close(); self.tray.hide()


def main():
    if "--daemon" in sys.argv:
        sys.argv.remove("--daemon")
        from .daemon import main as daemon_main
        return daemon_main()
    parser = argparse.ArgumentParser(description="ARISE · Desktop assistant")
    from .platforms import data_directory
    parser.add_argument("--data-dir", default=str(data_directory()))
    parser.add_argument("--shutdown", action="store_true", help="Cerrar interfaz, daemon y sus procesos para actualizar")
    parser.add_argument("--background", action="store_true")
    parser.add_argument("--settings", action="store_true")
    parser.add_argument("--setup", action="store_true", help="Completar la configuración de Gentle y herramientas después de instalar")
    parser.add_argument("--setup-pack", help="Configurar modelos y servidor desde el ZIP offline")
    parser.add_argument("--screenshot", help=argparse.SUPPRESS)
    parser.add_argument("--voice-smoke", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.voice_smoke:
        from .bundle import application_root
        from .models import probe_packaged_voice
        Path(args.voice_smoke).write_text(json.dumps(probe_packaged_voice(application_root()), indent=2), encoding='utf-8')
        return 0
    if args.shutdown:
        from .updates import shutdown_application
        return shutdown_application(args.data_dir)
    if os.name == 'nt':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('PRAXISGENAI.ARISE')
    app = QApplication.instance() or QApplication(sys.argv); app.setApplicationName(application_name()); app.setWindowIcon(icon()); app.setQuitOnLastWindowClosed(False)
    import hashlib
    address = "ARISE-" + hashlib.sha256(str(Path(args.data_dir).resolve()).encode()).hexdigest()[:20]
    client = QLocalSocket(); client.connectToServer(address)
    if client.waitForConnected(300):
        client.write(("setup-pack:"+str(Path(args.setup_pack).resolve())+"\n").encode() if args.setup_pack else (b"setup\n" if args.setup else b"settings\n" if args.settings else b"wake\n")); client.flush(); client.waitForBytesWritten(500); return 0
    local = QLocalServer()
    if not args.screenshot and not local.listen(address):
        QLocalServer.removeServer(address)
        if not local.listen(address): raise RuntimeError("No se pudo iniciar la instancia de ARISE.")
    if args.screenshot:
        runtime = Assistant(args.data_dir)
    else:
        from .daemon import ensure_daemon
        from .remote import RemoteAssistant
        runtime = RemoteAssistant(ensure_daemon(args.data_dir), args.data_dir)
    c = runtime.storage.config; pos = c["orb_position"]
    rect = app.primaryScreen().availableGeometry()
    x, y = pos if pos else (rect.right() - c["orb_size"] - 24, rect.top() + 40)
    app, orb = build_orb(app, c["orb_size"], x, y, c.get("orb_animation", "sprite"))
    orb.setWindowIcon(icon())
    app.setQuitOnLastWindowClosed(False)
    controller = Controller(app, runtime, orb, start_voice=not bool(args.screenshot))
    server = None
    if not getattr(runtime, "is_remote", False):
        server = make_server(runtime); threading.Thread(target=server.serve_forever, daemon=True).start()
    def connection():
        sock = local.nextPendingConnection()
        def read():
            command = bytes(sock.readAll()).decode().strip()
            if command == "shutdown": controller.quit_all()
            elif command == "settings": controller.show_settings()
            elif command == "wake": controller.wake()
            elif command == "setup": controller.install_gentle()
            elif command.startswith("setup-pack:"): controller.install_model_pack(command[len("setup-pack:"):])
            sock.disconnectFromServer()
        sock.readyRead.connect(read)
        sock.disconnected.connect(sock.deleteLater)
        if sock.bytesAvailable(): read()
    local.newConnection.connect(connection)
    if args.setup_pack: QTimer.singleShot(100,lambda:controller.install_model_pack(str(Path(args.setup_pack).resolve())))
    elif args.setup: QTimer.singleShot(100,controller.install_gentle)
    elif args.settings or not c["onboarding_complete"]: controller.show_settings()
    if args.screenshot:
        QTimer.singleShot(300, lambda: (orb.grab().save(args.screenshot), controller.quit()))
    try: return app.exec()
    finally:
        controller.close(); local.close()
        if server: server.shutdown(); server.server_close(); runtime.storage.db.close()

if __name__ == "__main__":
    raise SystemExit(main())
