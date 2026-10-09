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
from PySide6.QtCore import Qt, QTimer, QObject, Signal, QEvent, QPoint
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import (QApplication, QWidget, QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QTextBrowser, QTextEdit, QComboBox, QCheckBox, QTabWidget,
    QFileDialog, QMessageBox, QSystemTrayIcon, QMenu, QSpinBox, QDialogButtonBox, QInputDialog)
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
        tabs = QTabWidget(); layout.addWidget(tabs)
        self.fields, self.keys, self.mcp = {}, {}, {}
        config = self.runtime.storage.config
        voice = QWidget(); f = QFormLayout(voice); tabs.addTab(voice, "Voz y audio")
        self.fields["voice_provider"] = QComboBox(); self.fields["voice_provider"].addItems(["openai", "gemini", "local"])
        self.fields["voice_provider"].setCurrentText(config["voice_provider"])
        f.addRow("Proveedor", self.fields["voice_provider"])
        for key, label in (("voice_model", "Modelo de voz"), ("voice", "Voz"), ("wake_model", "Modelo Vosk (carpeta)"), ("local_stt_model", "Modelo Whisper local"), ("piper_model", "Modelo Piper (.onnx)")):
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
        self.check_field(f, "wake_enabled", "Escuchar 'Oye Arise' localmente", config["wake_enabled"])
        self.text_field(f, "wake_phrases", "Frases (separadas por coma)", ", ".join(config["wake_phrases"]))
        f.addRow(QLabel("Con auriculares puedes interrumpir la voz en la nube. La voz local funciona por turnos."))
        self.button(f, "Elegir carpeta Vosk", lambda: self.pick("wake_model", directory=True))
        self.button(f, "Descargar activación local en español", self.download_wake)
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
        for provider in ("openai", "gemini", "anthropic"):
            entry = QLineEdit(); entry.setEchoMode(QLineEdit.Password); entry.setPlaceholderText("Dejar vacío conserva la clave existente")
            self.keys[provider] = entry; f.addRow(provider, entry)
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
        self.button(f, "Guardar y comprobar herramientas", self.connect_tools)
        self.button(f, "Importar configuración MCP", self.import_tools)
        self.text_field(f, "extra_mcp", "MCP adicionales (objeto JSON)", "{}")
        f.addRow(QLabel("Los comandos son listas de ejecutables y argumentos; no cadenas de shell."))
        ui = QWidget(); f = QFormLayout(ui); tabs.addTab(ui, "Orbe")
        size = QSpinBox(); size.setRange(48, 240); size.setValue(config["orb_size"]); self.fields["orb_size"] = size
        f.addRow("Tamaño", size)
        self.check_field(f, "pinned", "Mantener visible en reposo", config["pinned"])
        self.check_field(f, "reduced_motion", "Reducir animación", config["reduced_motion"])
        self.fields["orb_animation"] = QComboBox(); self.fields["orb_animation"].addItems(["sprite", "native"]); self.fields["orb_animation"].setCurrentText(config["orb_animation"]); f.addRow("Animación", self.fields["orb_animation"])
        autostart = QCheckBox("Iniciar ARISE al entrar a Windows")
        autostart.setEnabled(os.name == "nt" and getattr(sys, "frozen", False))
        autostart.setChecked(self.autostart_enabled()); self.autostart = autostart; f.addRow(autostart)
        self.button(f, "Abrir carpeta de datos", controller.open_data)
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
        self.setWindowTitle("ARISE · Conversación"); self.resize(340, 500); self.setMinimumSize(300, 380); self.setMaximumWidth(440); self.setStyleSheet(STYLE)
        layout = QVBoxLayout(self)
        title = QLabel("ARISE"); title.setObjectName("title"); layout.addWidget(title)
        self.status = QLabel("Oye Arise · Ctrl+Alt+A para hablar"); self.status.setWordWrap(True); layout.addWidget(self.status)
        self.privacy = QLabel("Micrófono apagado · Control apagado"); self.privacy.setWordWrap(True); layout.addWidget(self.privacy)
        self.history = QTextBrowser(); self.history.setOpenExternalLinks(False); layout.addWidget(self.history)
        row = QHBoxLayout(); layout.addLayout(row)
        self.conversations = QComboBox(); self.conversations.setMinimumWidth(80); self.conversations.setMaximumWidth(170); self.conversations.currentIndexChanged.connect(self.select_conversation); row.addWidget(self.conversations)
        for label, callback in (("Nueva", self.new_conversation), ("Ajustes", controller.show_settings)):
            b = QPushButton(label); b.clicked.connect(callback); row.addWidget(b)
        self.input = QTextEdit(); self.input.setPlaceholderText("Pídele algo a ARISE…"); self.input.setMaximumHeight(58); layout.addWidget(self.input)
        row = QHBoxLayout(); layout.addLayout(row)
        for label, callback in (("Enviar", self.send), ("Hablar", controller.wake), ("Detener", controller.stop)):
            b = QPushButton(label); b.clicked.connect(lambda checked=False, cb=callback: cb()); row.addWidget(b)
        self.control = QCheckBox("Permitir control del PC"); self.control.toggled.connect(self.toggle_control); layout.addWidget(self.control)
        self.reload()

    def append(self, role, text):
        self.history.append(f'<p><b style="color:#74F6FF">{html.escape(role)}</b><br>{html.escape(text).replace(chr(10), "<br>")}</p>')

    def reload(self):
        self.history.clear()
        for message in self.runtime.storage.messages(self.runtime.conversation):
            self.append("Tú" if message["role"] == "user" else "ARISE", message["text"])
        self.conversations.blockSignals(True); self.conversations.clear()
        for c in self.runtime.storage.conversations(): self.conversations.addItem(c["title"], c["id"])
        self.conversations.setCurrentIndex(max(0, self.conversations.findData(self.runtime.conversation))); self.conversations.blockSignals(False)

    def send(self):
        text = self.input.toPlainText().strip()
        if text:
            self.input.clear(); self.controller.background(lambda: self.runtime.steer(text))

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
        self.settings_window = None
        self.panel = Panel(self)
        self.wake_requested.connect(self._wake); self.stop_requested.connect(self._stop)
        self.tray = QSystemTrayIcon(icon(), self); self.tray.setToolTip("ARISE · Oye Arise")
        self.menu = QMenu()
        for label, callback in (("Hablar", self.wake), ("Conversación", self.show_panel), ("Ajustes", self.show_settings),
                                ("Silenciar / activar micrófono", self.toggle_mute), ("Detener tareas", self.stop), ("Reiniciar asistente", self.restart), ("Salir de ARISE", self.quit_all), ("Cerrar panel y orbe", self.quit)):
            self.menu.addAction(label, callback)
        self.tray.setContextMenu(self.menu); self.tray.activated.connect(lambda reason: self.show_panel() if reason == QSystemTrayIcon.Trigger else None)
        if QSystemTrayIcon.isSystemTrayAvailable(): self.tray.show()
        self.orb.installEventFilter(self); self.press_point = None
        self.timer = QTimer(self); self.timer.timeout.connect(self.poll); self.timer.start(80)
        self.hotkeys = Hotkeys(self.wake, self.stop)
        if os.name == "nt" and not getattr(runtime, "is_remote", False) and not self.hotkeys.start(): self.runtime.emit("notice", {"text": "Algún atajo está ocupado; usa el orbe o la bandeja."})
        app.aboutToQuit.connect(self.close)
        if start_voice: self.voice.start()
        self.reconfigure()

    def background(self, operation, complete=None):
        worker = Worker(self); self.workers.append(worker)
        worker.finished.connect(lambda result: complete(result) if complete else None)
        worker.failed.connect(lambda text: self.runtime.emit("error", {"text": text}))
        def cleanup(*_):
            if worker in self.workers: self.workers.remove(worker)
            worker.deleteLater()
        worker.finished.connect(cleanup); worker.failed.connect(cleanup); worker.start(operation)

    def wake(self, initial=""):
        self.wake_requested.emit(initial if isinstance(initial, str) else "")

    def _wake(self, initial):
        self.orb.show(); self.orb.raise_(); self.voice.wake(initial)

    def stop(self): self.stop_requested.emit()

    def _stop(self):
        self.voice.end_session(); self.background(self.runtime.stop)

    def toggle_mute(self): self.voice.mute(not self.voice.muted)

    def show_panel(self): self.panel.show(); self.panel.raise_(); self.panel.activateWindow()

    def show_settings(self):
        if self.settings_window is None: self.settings_window = Settings(self)
        self.settings_window.show(); self.settings_window.raise_(); self.settings_window.activateWindow()

    def reconfigure(self):
        c = self.runtime.storage.config
        self.orb.apply_state({"size": c["orb_size"], "visible": c["pinned"], "reason": "OYE ARISE", "reduced_motion": c["reduced_motion"]})
        for timer in self.orb.findChildren(QTimer): timer.setInterval(200 if c["reduced_motion"] else 100 if c.get("orb_animation") == "sprite" else 33)
        self.clamp_position()

    def clamp_position(self):
        point = self.orb.pos()
        screen = self.app.screenAt(point) or self.app.primaryScreen()
        rect = screen.availableGeometry()
        self.orb.move(max(rect.left(), min(point.x(), rect.right() - self.orb.width() + 1)),
                      max(rect.top(), min(point.y(), rect.bottom() - self.orb.height() + 1)))

    def eventFilter(self, obj, event):
        if obj is self.orb:
            if event.type() == QEvent.MouseButtonPress:
                self.press_point = event.globalPosition().toPoint()
                if event.button() == Qt.RightButton:
                    self.menu.popup(self.press_point); return True
            elif event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                moved = self.press_point and (event.globalPosition().toPoint() - self.press_point).manhattanLength() > 6
                self.clamp_position()
                self.runtime.storage.config["orb_position"] = [self.orb.x(), self.orb.y()]
                self.runtime.storage.save_config(self.runtime.storage.config)
                if not moved: self.wake()
            elif event.type() == QEvent.MouseButtonDblClick:
                self.show_panel(); return True
            elif event.type() == QEvent.Close:
                self.orb.hide(); event.ignore(); return True
        return super().eventFilter(obj, event)

    def poll(self):
        try:
            result = self.runtime.events_after(self.cursor); self.cursor = result["cursor"]
        except RuntimeError:
            self.panel.status.setText("Proceso residente desconectado")
            return
        for event in result["events"]:
            kind, data = event["kind"], event["data"]
            if kind == "orb":
                active = data["state"] != "idle"
                self.orb.apply_state({"speaking": data["state"] == "speaking", "listening": data["state"] == "listening",
                    "reason": data["activity"], "state": data["state"], "privacy": data, "speaker": {"understanding": "subagent", "waiting_approval": "approval", "error": "error", "speaking": "human", "working": "working"}.get(data["state"], "orchestrator"),
                    "visible": active or self.runtime.storage.config["pinned"]})
                self.panel.status.setText(data["activity"])
                self.panel.privacy.setText("Micrófono " + ("activo" if data["microphone"] else "apagado") + " · Pantalla " + ("activa" if data["screen"] else "apagada") + " · Control " + ("activo" if data["control"] else "apagado"))
                self.panel.control.blockSignals(True); self.panel.control.setChecked(data["control"]); self.panel.control.blockSignals(False)
            elif kind in ("user", "assistant_end", "notice", "error"):
                self.panel.append({"user": "Tú", "assistant_end": "ARISE", "notice": "Aviso", "error": "Revisar"}[kind], data.get("text", ""))
                if kind == "error":
                    self.runtime.orb.update("error")
                    self.show_panel()
            elif kind == "voice_transcript": self.panel.append("Voz · " + data["role"], data["text"])
            elif kind == "approval": self.approval(data)
            elif kind == "dialog": self.dialog(data)

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
        dialog = QInputDialog(self.panel); dialog.setWindowTitle(data.get("title", "ARISE")); dialog.setLabelText(data.get("message", data.get("title", "Tu respuesta")))
        method = data["method"]
        if method in ("select", "confirm"):
            dialog.setComboBoxItems(data.get("options", []) if method == "select" else ["No", "Sí"]); dialog.setComboBoxEditable(False)
        else: dialog.setTextValue(str(data.get("prefill", "")))
        def answer(result):
            value = dialog.textValue()
            record = {"id": data["id"], "cancelled": result != QDialog.Accepted, "value": value, "confirmed": value == "Sí"}
            self.background(lambda: self.runtime.answer_dialog(record))
        dialog.finished.connect(answer); dialog.finished.connect(dialog.deleteLater); dialog.open()

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
            self.background(self.runtime.shutdown, lambda _: self.quit())
        else: self.quit()

    def quit(self):
        self.orb.removeEventFilter(self)
        self.app.quit()

    def close(self):
        if self.closed: return
        self.closed = True; self.timer.stop(); self.hotkeys.close(); self.voice.close(); self.runtime.close(); self.tray.hide()


def main():
    if "--daemon" in sys.argv:
        sys.argv.remove("--daemon")
        from .daemon import main as daemon_main
        return daemon_main()
    parser = argparse.ArgumentParser(description="ARISE · Orbe Windows")
    parser.add_argument("--data-dir", default=str(Path(os.getenv("LOCALAPPDATA", Path.home() / ".local" / "share")) / "ARISE-Orb"))
    parser.add_argument("--background", action="store_true")
    parser.add_argument("--settings", action="store_true")
    parser.add_argument("--screenshot", help=argparse.SUPPRESS)
    args = parser.parse_args()
    app = QApplication.instance() or QApplication(sys.argv); app.setApplicationName("ARISE"); app.setWindowIcon(icon()); app.setQuitOnLastWindowClosed(False)
    import hashlib
    address = "ARISE-" + hashlib.sha256(str(Path(args.data_dir).resolve()).encode()).hexdigest()[:20]
    client = QLocalSocket(); client.connectToServer(address)
    if client.waitForConnected(300):
        client.write(b"settings\n" if args.settings else b"wake\n"); client.flush(); client.waitForBytesWritten(500); return 0
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
            if command == "settings": controller.show_settings()
            elif command == "wake": controller.wake()
            sock.disconnectFromServer()
        sock.readyRead.connect(read)
        sock.disconnected.connect(sock.deleteLater)
        if sock.bytesAvailable(): read()
    local.newConnection.connect(connection)
    if args.settings or not c["onboarding_complete"]: controller.show_settings()
    if args.background and not c["pinned"]: orb.hide()
    if args.screenshot:
        QTimer.singleShot(300, lambda: (orb.grab().save(args.screenshot), controller.quit()))
    try: return app.exec()
    finally:
        controller.close(); local.close()
        if server: server.shutdown(); server.server_close(); runtime.storage.db.close()

if __name__ == "__main__":
    raise SystemExit(main())
