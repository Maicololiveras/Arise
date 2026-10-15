"""Bounded release notes with persistent, explicit update controls."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextBrowser, QPushButton


class UpdateDialog(QDialog):
    def __init__(self, manifest, current_version, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Actualizar ARISE')
        layout = QVBoxLayout(self)
        title = QLabel(f"ARISE {manifest['version']} disponible · Actual: {current_version}")
        title.setTextFormat(Qt.PlainText)
        title.setWordWrap(True)
        layout.addWidget(title)
        self.notes = QTextBrowser()
        self.notes.setAccessibleName('Novedades de la actualización')
        self.notes.setPlainText(manifest['notes'])
        self.notes.setOpenExternalLinks(False)
        self.notes.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.notes.setMinimumSize(0, 40)
        layout.addWidget(self.notes, 1)
        explanation = QLabel('Se guardará la sesión y se cerrarán los procesos de ARISE para instalar.')
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        self.install = QPushButton('Instalar actualización')
        self.dismiss = QPushButton('Cerrar · Más tarde')
        self.install.setAutoDefault(False)
        self.dismiss.setDefault(True)
        self.install.clicked.connect(self.accept)
        self.dismiss.clicked.connect(self.reject)
        layout.addWidget(self.install)
        layout.addWidget(self.dismiss)
        self.dismiss.setFocus()
        available = self.screen().availableGeometry()
        width = min(560, max(240, available.width() - 40))
        height = min(580, max(300, available.height() - 60))
        self.resize(width, height)
