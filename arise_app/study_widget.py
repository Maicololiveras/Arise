"""Visible consent and bounded settings for screen study assistance."""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QScrollArea, QWidget, QLabel, QPlainTextEdit, QSpinBox, QCheckBox, QPushButton

class StudyDialog(QDialog):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        conversation = controller.panel.current_chat
        self.setWindowTitle('ARISE · Modo estudio')
        self.resize(480, 480)
        layout = QVBoxLayout(self)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        body = QWidget(); form = QFormLayout(body); form.setRowWrapPolicy(QFormLayout.WrapAllRows)
        scroll.setWidget(body); layout.addWidget(scroll)
        hint = QLabel('Comparte primero el material en este chat. ARISE observará la pantalla periódicamente y explicará las preguntas. No hará clics ni enviará respuestas. Usa este modo donde esté permitido recibir ayuda. Las capturas se envían al modelo de este chat y quedan en su historial.')
        hint.setWordWrap(True); form.addRow(hint)
        context = QPlainTextEdit(); context.setPlaceholderText('Tema, objetivos y material de referencia ya compartido'); form.addRow('Contexto de estudio', context)
        interval = QSpinBox(); interval.setRange(10,300); interval.setValue(30); interval.setSuffix(' s'); form.addRow('Intervalo tras cada respuesta',interval)
        consent = QCheckBox('Permito observar mi pantalla durante este estudio'); form.addRow(consent)
        status = QLabel(); status.setWordWrap(True); layout.addWidget(status)
        start = QPushButton('Iniciar estudio'); start.setEnabled(False); consent.toggled.connect(start.setEnabled); layout.addWidget(start)
        close = QPushButton('Cerrar'); close.clicked.connect(self.reject); layout.addWidget(close)
        def begin():
            start.setEnabled(False)
            options = dict(conversation=conversation,context=context.toPlainText(),interval=interval.value(),consent=consent.isChecked())
            def failed(error):
                status.setText(str(error));start.setEnabled(consent.isChecked())
            controller.background(lambda:controller.runtime.study_control('start',**options),lambda _:self.accept(),failed)
        start.clicked.connect(begin)
