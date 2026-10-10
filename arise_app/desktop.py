"""Native ARISE orb, setup, conversation panel and tray. No embedded browser."""
from __future__ import annotations
import argparse
import html
import json
import os
import sys
import threading
import time
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QObject, Signal, QEvent, QPoint, QSize
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import (QApplication, QWidget, QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QTextBrowser, QTextEdit, QComboBox, QCheckBox, QTabWidget,
    QFileDialog, QMessageBox, QSystemTrayIcon, QMenu, QSpinBox, QDialogButtonBox, QInputDialog, QWidgetAction, QScrollArea)
from .orb import build_orb
from .assistant import Assistant
from .audio import Audio
from .voice import VoiceService
from .server import make_server
from .hotkeys import Hotkeys
from .bundle import configure_bundle

STYLE = """
QWidget {background:#0A1828;color:#EDF8FF;font-family:'Segoe UI';font-size:13px;}
QDialog {background:#0A1828;}
QLineEdit,QTextEdit,QTextBrowser,QComboBox,QSpinBox {background:#10283C;border:1px solid #25445B;border-radius:7px;padding:8px;selection-background-color:#2563EB;}
QPushButton {background:#14394A;border:1px solid #2F6878;border-radius:7px;padding:9px 16px;}
QPushButton:hover {background:#205368;} QPushButton:disabled {color:#7292A8;}
QLabel#title {font-size:24px;font-weight:700;color:#74F6FF;}
QLabel#chatTitle {font-size:18px;font-weight:600;color:#EDF8FF;}
QLabel#chatStatus,QLabel#chatPrivacy {font-size:11px;color:#9DB3C7;}
QTextBrowser#chatHistory {background:transparent;border:0;padding:3px;}
QPushButton#iconButton {padding:6px;border:0;background:transparent;border-radius:8px;}
QPushButton#iconButton:hover {background:#17364C;}
QPushButton#iconButton:checked {background:#205368;border:1px solid #74F6FF;}
QTabWidget::pane {border:1px solid #25445B;} QTabBar::tab {padding:12px;background:#10283C;}
QTabBar::tab:selected {color:#74F6FF;background:#17364C;}
QCheckBox {padding:5px;} QMenu {background:#10283C;}
"""

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
        "mic": '<rect x="9" y="2" width="6" height="13" rx="3"/><path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3M8 22h8"/>',
        "stop": '<rect x="5" y="5" width="14" height="14" rx="2"/>',
        "plus": '<path d="M12 4v16M4 12h16"/>',
    }
    from PySide6.QtSvg import QSvgRenderer
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="#B9D6E7" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">' + paths[name] + '</g></svg>'
    pix = QPixmap(24, 24); pix.fill(Qt.transparent)
    painter = QPainter(pix); QSvgRenderer(svg.encode()).render(painter); painter.end()
    return QIcon(pix)


def icon():
    pix = QPixmap(64, 64); pix.fill(Qt.transparent)
    p = QPainter(pix)
    from PySide6.QtSvg import QSvgRenderer
    import assets
    source = Path(assets.__file__).parent / "icon.svg"
    QSvgRenderer(str(source)).render(p)
    p.end()
    return QIcon(pix)

class Settings(QDialog):
    saved = Signal()
    def __init__(self, controller):
        super().__init__()
        self.controller, self.runtime = controller, controller.runtime
        self.setWindowTitle("ARISE · Configuración")
        self.resize(760, 650); self.setStyleSheet(STYLE)
        layout = QVBoxLayout(self)
        title = QLabel("Configura tu ARISE"); title.setObjectName("title"); layout.addWidget(title)
        layout.addWidget(QLabel("Elige voz, conecta el agente y habilita las herramientas que usarás."))
        quick_setup=QPushButton("Configurar todo desde ZIP")
        quick_setup.clicked.connect(controller.install_model_pack);layout.addWidget(quick_setup)
        gentle_setup=QPushButton("Configurar Gentle · estable o último main")
        gentle_setup.clicked.connect(controller.install_gentle);layout.addWidget(gentle_setup)
        tabs = QTabWidget(); layout.addWidget(tabs)
        self.fields, self.keys, self.mcp = {}, {}, {}
        config = self.runtime.storage.config
        voice = QWidget(); f = QFormLayout(voice); tabs.addTab(voice, "Voz y audio")
        self.fields["voice_provider"] = QComboBox(); self.fields["voice_provider"].addItems(["openai", "gemini", "local"])
        self.fields["voice_provider"].setCurrentText(config["voice_provider"])
        f.addRow("Proveedor", self.fields["voice_provider"])
        self.fields["local_stt_engine"] = QComboBox(); self.fields["local_stt_engine"].addItems(["auto", "vosk", "faster-whisper", "openai-whisper"])
        self.fields["local_stt_engine"].setCurrentText(config["local_stt_engine"]); f.addRow("Motor local", self.fields["local_stt_engine"])
        for key, label in (("voice_model", "Modelo de voz"), ("voice", "Voz"), ("wake_model", "Modelo Vosk (carpeta)"), ("local_stt_model", "Modelo local (.pt o carpeta)"), ("piper_model", "Modelo Piper (.onnx)")):
            self.text_field(f, key, label, config[key])
        self.fields["voice_provider"].currentTextChanged.connect(self.provider_changed)
        devices = []
        try:
            devices = Audio.devices()
        except Exception:
            f.addRow(QLabel("No se detectaron dispositivos. Revisa el audio del sistema."))
        for key, label, capability in (("input_device", "Micrófono", "input"), ("output_device", "Altavoz", "output")):
            combo = QComboBox(); combo.addItem("Predeterminado del sistema", None)
            for device in devices:
                if device[capability]:
                    combo.addItem(device["name"], device["id"])
            idx = combo.findData(config[key]); combo.setCurrentIndex(max(0, idx)); self.fields[key] = combo; f.addRow(label, combo)
        self.check_field(f, 'local_dialogue_enabled', 'Conversar con un modelo local mientras Gentle trabaja', config['local_dialogue_enabled'])
        self.text_field(f,'local_dialogue_url','Servidor conversacional local',config['local_dialogue_url'])
        self.text_field(f,'local_server_command','Arranque local (JSON)',json.dumps(config['local_server_command']))
        self.text_field(f,'local_dialogue_model','Modelo local (vacío: detectar)',config['local_dialogue_model'])
        self.check_field(f, "local_barge_in", "Permitir interrupciones en voz local", config["local_barge_in"])
        threshold=QSpinBox(); threshold.setRange(300,10000); threshold.setValue(config["voice_interrupt_threshold"]); self.fields["voice_interrupt_threshold"]=threshold; f.addRow("Umbral de interrupción local",threshold)
        self.check_field(f, "wake_enabled", "Escuchar 'Oye Arise' localmente", config["wake_enabled"])
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
        for key, label in (("workspace", "Carpeta de trabajo"), ("pi_command", "Comando Pi (lista JSON)"), ("gentle_path", "Carpeta Gentle Shell"), ("agent_provider", "Proveedor del agente"), ("agent_model", "Modelo del agente")):
            value = json.dumps(config[key]) if key == "pi_command" else config[key]
            self.text_field(f, key, label, value)
        self.fields["thinking"] = QComboBox(); self.fields["thinking"].addItems(["off", "minimal", "low", "medium", "high", "xhigh"])
        self.fields["thinking"].setCurrentText(config["thinking"]); f.addRow("Esfuerzo", self.fields["thinking"])
        self.check_field(f, "code_enabled", "Permitir herramientas de código y shell de Pi", config["code_enabled"])
        self.button(f, "Elegir carpeta de trabajo", lambda: self.pick("workspace", True))
        self.button(f, "Elegir Gentle Shell", lambda: self.pick("gentle_path", True))
        self.button(f, "Conectar y listar modelos", self.models)
        self.button(f, "Abrir Pi para /login", controller.open_pi)
        self.button(f, "Detectar Pi y Gentle Shell", self.detect_agent)
        f.addRow(QLabel("Dejar proveedor/modelo vacíos conserva la selección existente de Pi."))
        keys = QWidget(); f = QFormLayout(keys); tabs.addTab(keys, "Credenciales")
        for provider in ("openai", "gemini", "anthropic", "github-updates", "local-dialogue"):
            entry = QLineEdit(); entry.setEchoMode(QLineEdit.Password); entry.setPlaceholderText("Dejar vacío conserva la clave existente")
            self.keys[provider] = entry; f.addRow(provider, entry)
        f.addRow(QLabel("GitHub: acceso a actualizaciones y herramientas privadas. Se detecta también una sesión existente de gh."))
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
        self.button(f, "Instalar y reparar dependencias", self.setup_desktop_tools)
        self.button(f, "Guardar y comprobar herramientas", self.connect_tools)
        self.button(f, "Importar configuración MCP", self.import_tools)
        self.text_field(f, "extra_mcp", "MCP adicionales (objeto JSON)", "{}")
        f.addRow(QLabel("Los comandos son listas de ejecutables y argumentos; no cadenas de shell."))
        ui = QWidget(); f = QFormLayout(ui); tabs.addTab(ui, "Orbe")
        size = QSpinBox(); size.setRange(48, 240); size.setValue(config["orb_size"]); self.fields["orb_size"] = size
        f.addRow("Tamaño", size)
        self.check_field(f, "pinned", "Orbe siempre visible", True); self.fields["pinned"].setEnabled(False)
        self.check_field(f, "reduced_motion", "Reducir animación", config["reduced_motion"])
        self.fields["orb_animation"] = QComboBox(); self.fields["orb_animation"].addItems(["sprite", "native"]); self.fields["orb_animation"].setCurrentText(config["orb_animation"]); f.addRow("Animación", self.fields["orb_animation"])
        autostart = QCheckBox("Iniciar ARISE al entrar a Windows")
        autostart.setEnabled(os.name == "nt" and getattr(sys, "frozen", False))
        autostart.setChecked(self.autostart_enabled()); self.autostart = autostart; f.addRow(autostart)
        self.button(f, "Abrir carpeta de datos", controller.open_data)
        pages = [(tabs.widget(i), tabs.tabText(i)) for i in range(tabs.count())]
        while tabs.count(): tabs.removeTab(0)
        for page, label in pages:
            scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(page); tabs.addTab(scroll, label)
        self.message = QLabel(""); self.message.setWordWrap(True); layout.addWidget(self.message)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Close)
        buttons.button(QDialogButtonBox.Save).setText("Guardar"); buttons.button(QDialogButtonBox.Close).setText("Cerrar")
        buttons.accepted.connect(self.save); buttons.rejected.connect(self.hide); layout.addWidget(buttons)

    def text_field(self, form, key, label, value):
        field = QLineEdit(str(value)); self.fields[key] = field; form.addRow(label, field)

    def check_field(self, form, key, label, value):
        field = QCheckBox(label); field.setChecked(value); self.fields[key] = field; form.addRow(field)

    def button(self, form, label, callback):
        button = QPushButton(label); button.clicked.connect(callback); form.addRow(button)

    def pick(self, key, directory=False):
        value = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta") if directory else QFileDialog.getOpenFileName(self, "Seleccionar archivo")[0]
        if value:
            self.fields[key].setText(value)

    def provider_changed(self, provider):
        if provider == "openai":
            self.fields["voice_model"].setText("gpt-realtime-2.1"); self.fields["voice"].setText("marin")
        elif provider == "gemini":
            self.fields["voice_model"].setText("gemini-3.1-flash-live-preview"); self.fields["voice"].setText("Aoede")
        else:
            self.fields["voice_model"].setText("local"); self.fields["voice"].setText("Windows default")

    def changes(self):
        changes = {}
        for key, field in self.fields.items():
            if isinstance(field, QCheckBox): value = field.isChecked()
            elif isinstance(field, QSpinBox): value = field.value()
            elif isinstance(field, QComboBox): value = field.currentData() if key.endswith("_device") else field.currentText()
            else: value = field.text().strip()
            changes[key] = value
        changes["pi_command"] = json.loads(changes["pi_command"])
        changes["local_server_command"] = json.loads(changes["local_server_command"])
        changes["wake_phrases"] = [v.strip().lower() for v in changes["wake_phrases"].split(",") if v.strip()]
        extra = json.loads(changes.pop("extra_mcp"))
        if not isinstance(extra, dict): raise ValueError("MCP adicionales debe ser un objeto JSON")
        changes["mcp"] = {**{name: {"command": json.loads(command.text()), "enabled": enabled.isChecked()} for name, (enabled, command) in self.mcp.items()}, **extra}
        changes["onboarding_complete"] = True
        return changes

    def save(self):
        try:
            self.controller.voice.end_session()
            if self.controller.voice.active.is_set():
                raise RuntimeError("Termina la conversación de voz antes de guardar.")
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

    def test_voice(self):
        if self.save(): self.controller.wake("Saluda brevemente y confirma que escuchas.")

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

    def setup_desktop_tools(self):
        if not self.save(): return
        self.message.setText('Instalando pantalla, control, transcripción y Forge…')
        def complete(result):
            self.message.setText('Dependencias instaladas. Herramientas: '+str(result.get('catalogs',{})))
            self.controller.settings_window=None; self.hide()
            self.controller.show_settings()
        self.controller.background(lambda:self.runtime.request('tools/setup-desktop',{},timeout=2400),complete,lambda message:self.message.setText(message))

    def detect_agent(self):
        from .discovery import detect
        found = detect(self.runtime.storage.config)
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

class Panel(QWidget):
    def __init__(self, controller):
        super().__init__(); self.controller = controller; self.runtime = controller.runtime
        self.setWindowTitle("ARISE Assistant"); self.resize(360, 540); self.setMinimumSize(320, 400); self.setMaximumWidth(520); self.setStyleSheet(STYLE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 10); layout.setSpacing(7)
        title = QLabel("ARISE Assistant"); title.setObjectName("chatTitle"); layout.addWidget(title)
        self.status = QLabel("Listo para ayudarte"); self.status.setObjectName("chatStatus"); self.status.hide()
        self.privacy = QLabel("Micrófono apagado · Control apagado"); self.privacy.setObjectName("chatPrivacy"); self.privacy.setWordWrap(True); self.privacy.hide()
        self.history = QTextBrowser(); self.history.setObjectName("chatHistory"); self.history.setOpenExternalLinks(False); layout.addWidget(self.history, 1)
        self.input = ChatInput(); self.input.setPlaceholderText("Escribe a ARISE…"); self.input.setFixedHeight(58)
        self.input.setToolTip("Enter para enviar · Shift+Enter para otra línea"); self.input.submitted.connect(self.send); layout.addWidget(self.input)
        row = QHBoxLayout(); row.setSpacing(3); layout.addLayout(row)
        self.navigation = self.icon_button(row, "menu", "Proyectos, chats y comandos")
        self.navigation_menu = QMenu(self.navigation)
        picker = QWidget(); pick_layout = QFormLayout(picker); pick_layout.setContentsMargins(10, 8, 10, 8)
        self.projects = QComboBox(); self.projects.currentIndexChanged.connect(self.select_project); pick_layout.addRow("Proyecto", self.projects)
        self.conversations = QComboBox(); self.conversations.currentIndexChanged.connect(self.select_conversation); pick_layout.addRow("Chat", self.conversations)
        action = QWidgetAction(self.navigation_menu); action.setDefaultWidget(picker); self.navigation_menu.addAction(action)
        self.navigation_menu.addAction(control_icon("plus"), "Nuevo chat", self.new_conversation)
        self.navigation_menu.addAction(control_icon("folder"), "Elegir carpeta…", self.open_project)
        self.navigation_menu.addAction("Configurar todo desde ZIP…", controller.install_model_pack)
        self.navigation_menu.addAction(control_icon("settings"), "Ajustes…", controller.show_settings)
        menu = self.navigation_menu.addMenu("Comandos de la sesión"); self.commands_menu = menu; self.commands_loading = False
        menu.aboutToShow.connect(self.refresh_commands)
        for command in ("/gentle:profiles", "/gentle:models", "/gentle:status", "/gentle:commands"):
            menu.addAction(command, lambda checked=False, value=command: self.controller.background(lambda: self.runtime.session_command(value)))
        self.control = QCheckBox("Permitir control del PC"); self.control.toggled.connect(self.toggle_control)
        permission = QWidgetAction(self.navigation_menu); permission.setDefaultWidget(self.control); self.navigation_menu.addAction(permission)
        self.navigation.setMenu(self.navigation_menu)
        self.folder_button = self.icon_button(row, "folder", "Elegir carpeta del proyecto", self.open_project)
        self.icon_button(row, "settings", "Ajustes", controller.show_settings)
        row.addStretch(1)
        self.icon_button(row, "stop", "Detener voz y tarea", controller.stop)
        self.send_button = self.icon_button(row, "send", "Enviar · Enter", self.send)
        self.mic_button = self.icon_button(row, "mic", "Hablar con ARISE", self.toggle_voice)
        self.mic_button.setCheckable(True)
        self.reload()

    @staticmethod
    def icon_button(row, name, label, callback=None):
        button = QPushButton(); button.setObjectName("iconButton"); button.setIcon(control_icon(name)); button.setIconSize(QSize(20, 20))
        button.setFixedSize(34, 34); button.setToolTip(label); button.setAccessibleName(label)
        if callback: button.clicked.connect(lambda checked=False: callback())
        row.addWidget(button); return button

    def toggle_voice(self):
        def operation():
            if self.controller.voice.active.is_set(): self.controller.voice.end_session()
            else: self.controller.voice.wake()
        self.controller.background(operation)

    def append(self, role, text):
        self.history.append(f'<p><b style="color:#74F6FF">{html.escape(role)}</b><br>{html.escape(text).replace(chr(10), "<br>")}</p>')

    def reload(self):
        catalog = self.runtime.project_catalog(); self.current_chat = catalog["active"]["conversation"]
        self.history.clear()
        for message in self.runtime.storage.messages(self.current_chat):
            self.append({"user":"Tú","voice_user":"Voz · Tú","voice_assistant":"Voz · ARISE"}.get(message["role"],"ARISE"), message["text"])
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
        if self.commands_loading: return
        self.commands_loading = True; chat = self.current_chat
        def operation():
            self.runtime.connect_pi()
            return self.runtime.pi.request({"type":"get_commands"}).get("data", {}).get("commands", [])
        def done(commands):
            self.commands_loading = False
            if chat != self.current_chat: return
            self.commands_menu.clear()
            for command in sorted((c for c in commands if c.get("source") == "extension"), key=lambda c:c["name"]):
                name = "/" + command["name"]
                action = self.commands_menu.addAction(name, lambda checked=False, value=name:self.run_command(value))
                action.setToolTip(command.get("description", ""))
        self.controller.background(operation, done, failed=lambda _:setattr(self, "commands_loading", False))

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

    def send(self):
        text = self.input.toPlainText().strip()
        if text:
            self.input.clear()
            if text.startswith("/"): self.run_command(text)
            else: self.controller.background(lambda: self.runtime.steer(text))

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
        self.panel = Panel(self)
        self.wake_requested.connect(self._wake); self.stop_requested.connect(self._stop)
        self.tray = QSystemTrayIcon(icon(), self); self.tray.setToolTip("ARISE · Oye Arise")
        self.menu = QMenu()
        for label, callback in (("Hablar", self.wake), ("Conversación", self.show_panel), ("Ajustes", self.show_settings),
                                ("Silenciar / activar micrófono", self.toggle_mute), ("Detener tareas", self.stop), ("Reiniciar asistente", self.restart), ("Salir de ARISE", self.quit_all), ("Ocultar conversación", self.hide_panel), ("Buscar actualizaciones", self.check_updates)):
            self.menu.addAction(label, callback)
        self.tray.setContextMenu(self.menu); self.tray.activated.connect(lambda reason: self.show_panel() if reason == QSystemTrayIcon.Trigger else None)
        if QSystemTrayIcon.isSystemTrayAvailable(): self.tray.show()
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

    def wake(self, initial=""):
        self.wake_requested.emit(initial if isinstance(initial, str) else "")

    def _wake(self, initial):
        self.last_interaction = time.monotonic()
        self.orb.show(); self.orb.raise_(); self.background(lambda:self.voice.wake(initial))

    def stop(self): self.stop_requested.emit()

    def _stop(self):
        self.close_dialogs()
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
        if self.panel.isVisible() and time.monotonic() - self.last_interaction >= 60:
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
        if self.closed: return
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
        box = QMessageBox(self.orb); box.setWindowTitle("Nueva versión de ARISE Assistant")
        box.setTextFormat(Qt.PlainText)
        box.setText(f"ARISE {manifest['version']} está disponible (actual: {__version__}).")
        box.setInformativeText(manifest['notes'] + "\n\n¿Descargar e instalar? Se guardará la sesión y se cerrarán los procesos de ARISE.")
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No); box.setDefaultButton(QMessageBox.No)
        box.button(QMessageBox.Yes).setText("Instalar actualización"); box.button(QMessageBox.No).setText("Más tarde")
        box.finished.connect(lambda result: self.download_and_install(manifest) if result == QMessageBox.Yes else None)
        self.update_dialog = box; box.open()

    def download_and_install(self, manifest):
        from .updates import download_update, launch_update
        from .bundle import application_root
        if self.update_busy: return
        self.update_busy = True; self.tray.setToolTip("ARISE · Descargando actualización…")
        def complete(installer):
            try:
                launch_update(installer, manifest, self.runtime.storage.root, application_root())
            except Exception as error: failed(str(error)); return
            self.close_dialogs()
            self.background(self.runtime.shutdown if getattr(self.runtime, "is_remote", False) else self.runtime.close, lambda _:self.quit(), lambda _:self.quit())
        def failed(message):
            self.update_busy = False; self.tray.setToolTip("ARISE Assistant")
            box = QMessageBox(self.orb); box.setWindowTitle("ARISE · Actualización")
            box.setTextFormat(Qt.PlainText); box.setText(message); self.update_dialog = box; box.open()
        self.background(lambda:Path(self.runtime.request("updates/download",{"manifest":manifest},timeout=600)["path"]) if getattr(self.runtime,"is_remote",False) else download_update(manifest, self.runtime.storage.root), complete, failed)

    def reconfigure(self):
        c = self.runtime.storage.config
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
                self.double_click = False
                self.press_point = event.globalPosition().toPoint()
                if event.button() == Qt.RightButton:
                    self.menu.popup(self.press_point); return True
            elif event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                moved = self.press_point and (event.globalPosition().toPoint() - self.press_point).manhattanLength() > 6
                self.clamp_position()
                self.position_timer.start()
                if self.double_click: self.double_click = False
                elif not moved: self.hide_panel()
            elif event.type() == QEvent.MouseButtonDblClick:
                self.double_click = True; self.show_panel(); return True
            elif event.type() == QEvent.Close:
                event.ignore(); self.hide_panel(); return True
        return super().eventFilter(obj, event)

    def poll(self):
        try:
            result = self.runtime.events_after(self.cursor); self.cursor = result["cursor"]
        except RuntimeError:
            self.panel.status.setText("Proceso residente desconectado")
            return
        for event in result["events"]:
            kind, data = event["kind"], event["data"]
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
            if kind == "orb":
                active = data["state"] != "idle"
                self.orb.apply_state({"speaking": data["state"] == "speaking", "listening": data["state"] == "listening",
                    "reason": data["activity"], "state": data["state"], "privacy": data, "speaker": {"understanding": "subagent", "waiting_approval": "approval", "error": "error", "speaking": "human", "working": "working"}.get(data["state"], "orchestrator"),
                    "visible": True})
                self.panel.status.setText(data["activity"])
                self.panel.send_button.setToolTip(data["activity"])
                self.panel.mic_button.setToolTip("Micrófono " + ("activo" if data["microphone"] else "apagado"))
                self.panel.mic_button.setAccessibleName(self.panel.mic_button.toolTip())
                self.panel.control.setText("Control del PC " + ("activo" if data["control"] else "apagado"))
                self.panel.privacy.setText("Micrófono " + ("activo" if data["microphone"] else "apagado") + " · Pantalla " + ("activa" if data["screen"] else "apagada") + " · Control " + ("activo" if data["control"] else "apagado"))
                self.panel.control.blockSignals(True); self.panel.control.setChecked(data["control"]); self.panel.control.blockSignals(False)
                self.panel.mic_button.setChecked(data["microphone"] and data["state"] not in ("idle", "wake_detected"))
            elif kind in ("user", "assistant_end", "notice", "error"):
                self.panel.append({"user": "Tú", "assistant_end": "ARISE", "notice": "Aviso", "error": "Revisar"}[kind], data.get("text", ""))
                if kind == "error":
                    self.runtime.orb.update("error")
                    self.tray.setToolTip('ARISE · '+data.get('text','Revisar aviso')[:200])
            elif kind == "voice_transcript":
                if data['role']=='user': self.last_interaction=time.monotonic()
                self.panel.append("Voz · " + data["role"], data["text"])
            elif kind == "input_text": self.panel.input.setPlainText(data["text"]); self.panel.input.setFocus()
            elif kind == "approval": self.approval(data)
            elif kind == "dialog":
                if not (self.runtime.storage.config['voice_provider']=='local' and self.voice.active.is_set()): self.dialog(data)
            elif kind == "dialog_resolved":
                dialog=self.pending_dialogs.pop(data['id'],None)
                if dialog: dialog.setProperty('arise_cancelled',True); dialog.reject()

    def approval(self, data):
        # Nonmodal: stop hotkey, cancellation and microphone state keep updating.
        box = QMessageBox(self.panel); box.setWindowTitle("ARISE · Revisar envío")
        box.setText("¿Enviar este borrador de Gmail?"); box.setInformativeText(json.dumps(data["preview"], ensure_ascii=False, indent=2))
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No); box.setDefaultButton(QMessageBox.No)
        box.button(QMessageBox.Yes).setText("Permitir"); box.button(QMessageBox.No).setText("Cancelar")
        box.finished.connect(lambda result: self.answer_approval(data["id"], result == QMessageBox.Yes)); box.finished.connect(box.deleteLater)
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
        if data["method"] == "editor":
            dialog = QDialog(self.panel); dialog.setWindowTitle(data.get("title", "ARISE")); dialog.resize(560, 400)
            layout = QVBoxLayout(dialog); editor = QTextEdit(); editor.setPlainText(str(data.get("prefill", ""))); layout.addWidget(editor)
            buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); layout.addWidget(buttons)
            buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject)
            dialog.finished.connect(lambda result:submit(dialog,result,editor.toPlainText()))
            track(dialog); return
        dialog = QInputDialog(self.panel); dialog.setWindowTitle(data.get("title", "ARISE")); dialog.setLabelText(data.get("message", data.get("title", "Tu respuesta")))
        method = data["method"]
        if method in ("select", "confirm"):
            dialog.setComboBoxItems(data.get("options", []) if method == "select" else ["No", "Sí"]); dialog.setComboBoxEditable(False)
        else: dialog.setTextValue(str(data.get("prefill", "")))
        def answer(result):
            value = dialog.textValue()
            submit(dialog,result,value,value == "Sí")
        dialog.finished.connect(answer); track(dialog)

    def open_pi(self):
        if os.name != "nt":
            self.runtime.emit("notice", {"text": "Ejecuta Pi y /login en tu terminal."}); return
        from .processes import executable_argv
        import subprocess
        command = executable_argv(self.runtime.storage.config["pi_command"])
        subprocess.Popen(command, cwd=self.runtime.storage.config["workspace"], creationflags=subprocess.CREATE_NEW_CONSOLE)

    def open_data(self):
        if os.name == "nt": os.startfile(str(self.runtime.storage.root))

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

    def quit_all(self):
        if getattr(self.runtime, "is_remote", False):
            self.background(self.runtime.shutdown, lambda _: self.quit(), lambda _: self.quit())
        else: self.quit()

    def quit(self):
        self.app.removeEventFilter(self)
        self.app.quit()

    def close(self):
        if self.closed: return
        self.closed = True; self.app.removeEventFilter(self); self.timer.stop(); self.idle_timer.stop(); self.position_timer.stop(); self.hotkeys.close(); self.voice.close(); self.runtime.close(); self.tray.hide()


def main():
    if "--daemon" in sys.argv:
        sys.argv.remove("--daemon")
        from .daemon import main as daemon_main
        return daemon_main()
    parser = argparse.ArgumentParser(description="ARISE · Orbe Windows")
    parser.add_argument("--data-dir", default=str(Path(os.getenv("LOCALAPPDATA", Path.home() / ".local" / "share")) / "ARISE-Orb"))
    parser.add_argument("--shutdown", action="store_true", help="Cerrar interfaz, daemon y sus procesos para actualizar")
    parser.add_argument("--background", action="store_true")
    parser.add_argument("--settings", action="store_true")
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
    app = QApplication.instance() or QApplication(sys.argv); app.setApplicationName("ARISE"); app.setWindowIcon(icon()); app.setQuitOnLastWindowClosed(False)
    import hashlib
    address = "ARISE-" + hashlib.sha256(str(Path(args.data_dir).resolve()).encode()).hexdigest()[:20]
    client = QLocalSocket(); client.connectToServer(address)
    if client.waitForConnected(300):
        client.write(("setup-pack:"+str(Path(args.setup_pack).resolve())+"\n").encode() if args.setup_pack else (b"settings\n" if args.settings else b"wake\n")); client.flush(); client.waitForBytesWritten(500); return 0
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
            elif command.startswith("setup-pack:"): controller.install_model_pack(command[len("setup-pack:"):])
            sock.disconnectFromServer()
        sock.readyRead.connect(read)
        sock.disconnected.connect(sock.deleteLater)
        if sock.bytesAvailable(): read()
    local.newConnection.connect(connection)
    if args.setup_pack: QTimer.singleShot(100,lambda:controller.install_model_pack(str(Path(args.setup_pack).resolve())))
    elif args.settings or not c["onboarding_complete"]: controller.show_settings()
    if args.screenshot:
        QTimer.singleShot(300, lambda: (orb.grab().save(args.screenshot), controller.quit()))
    try: return app.exec()
    finally:
        controller.close(); local.close()
        if server: server.shutdown(); server.server_close(); runtime.storage.db.close()

if __name__ == "__main__":
    raise SystemExit(main())
