"""Bounded, searchable command catalog; selection never bypasses runtime approval."""
import unicodedata
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QLabel, QDialogButtonBox


def searchable(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text.casefold()) if not unicodedata.combining(c))


class CommandPicker(QDialog):
    def __init__(self, parent, selected):
        super().__init__(parent)
        self.setWindowTitle('Comandos de la sesión')
        self.selected = selected
        self.commands = []
        layout = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText('Buscar por nombre o descripción…')
        self.search.setAccessibleName('Buscar comandos')
        layout.addWidget(self.search)
        self.status = QLabel('Cargando comandos de la sesión…')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.results = QListWidget()
        self.results.setAccessibleName('Comandos disponibles')
        self.results.setStyleSheet('QListWidget::item {padding:6px;}')
        self.results.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.results.setTextElideMode(Qt.ElideRight)
        layout.addWidget(self.results, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.button(QDialogButtonBox.Close).setText('Cerrar')
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.search.textChanged.connect(self.filter)
        self.search.returnPressed.connect(self.choose)
        self.results.itemActivated.connect(lambda _: self.choose())
        bounds = self.screen().availableGeometry()
        self.resize(min(480, max(240, bounds.width()-40)), min(460, max(200, bounds.height()-80)))
        self.setMaximumSize(bounds.size())
        self.search.setFocus()

    def set_commands(self, commands):
        self.commands = sorted((c for c in commands if c.get('source') == 'extension' and isinstance(c.get('name'), str)), key=lambda c:c['name'])
        self.filter()

    def filter(self):
        query = searchable(self.search.text()).split()
        self.results.clear()
        for command in self.commands:
            name = '/' + command['name']
            description = str(command.get('description') or '')
            haystack = searchable(name + ' ' + description)
            if not all(word in haystack for word in query):
                continue
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, name)
            item.setToolTip(name + '\n' + description)
            item.setData(Qt.AccessibleDescriptionRole, description)
            self.results.addItem(item)
        count = self.results.count()
        self.status.setText(f'{count} de {len(self.commands)} comandos · Enter para ejecutar · Esc para cerrar' if count else 'Sin comandos que coincidan con la búsqueda.')
        if count:
            self.results.setCurrentRow(0)

    def choose(self):
        item = self.results.currentItem()
        if item is None:
            return
        command = item.data(Qt.UserRole)
        self.accept()
        self.selected(command)
