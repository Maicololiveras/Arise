"""Scrollable agent questions with persistent response and cancellation controls."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QTextBrowser, QLineEdit,
    QComboBox, QPlainTextEdit, QDialogButtonBox)


class TaskDialog(QDialog):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.method = data['method']
        self.setWindowTitle(str(data.get('title', 'ARISE'))[:160])
        layout = QVBoxLayout(self)
        self.details = QTextBrowser()
        self.details.setPlainText(str(data.get('message') or data.get('title') or 'Tu respuesta'))
        self.details.setOpenExternalLinks(False)
        self.details.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.details.setMinimumSize(0, 40)
        layout.addWidget(self.details, 1)
        self.input = None
        if self.method == 'select':
            self.input = QComboBox()
            self.input.addItems([str(item) for item in data.get('options', [])])
            self.input.setMinimumWidth(0)
            self.input.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        elif self.method == 'editor':
            self.input = QPlainTextEdit(str(data.get('prefill', '')))
            self.input.setMinimumSize(0, 40)
        elif self.method != 'confirm':
            self.input = QLineEdit(str(data.get('prefill', '')))
        if self.input is not None:
            layout.addWidget(self.input, 1 if self.method == 'editor' else 0)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.accept_button = self.buttons.button(QDialogButtonBox.Ok)
        self.reject_button = self.buttons.button(QDialogButtonBox.Cancel)
        self.accept_button.setText('Aceptar')
        self.reject_button.setText('Rechazar' if self.method == 'confirm' else 'Cancelar')
        self.accept_button.setAutoDefault(False)
        self.reject_button.setDefault(True)
        if self.method == 'select' and not data.get('options'):
            self.accept_button.setEnabled(False)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        available = self.screen().availableGeometry()
        self.resize(min(600, available.width()-40), min(460, available.height()-60))
        self.reject_button.setFocus()

    def value(self):
        if self.method == 'confirm': return 'Sí' if self.result() == QDialog.Accepted else 'No'
        if self.method == 'select': return self.input.currentText()
        if self.method == 'editor': return self.input.toPlainText()
        return self.input.text()
