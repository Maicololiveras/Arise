"""Keyboard surface for session-owned Gentle components inside the chat."""
import html
import re
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QTextBrowser, QVBoxLayout

COLORS = ['#252525','#fa8484','#8ee5ab','#ffd27c','#92bcff','#ed9bfa','#7ee4e4','#e0e6ee']


def rich_frame(frame):
    pieces, style = [], {}
    # Only SGR colour/style sequences are interpreted; all visible text is escaped.
    for part in re.split(r'(\x1b\[[0-9;]*m)', frame[:64000]):
        if not part.startswith('\x1b[') or not re.fullmatch(r'\x1b\[[0-9;]*m', part):
            safe = re.sub(r'\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b\[[0-?]*[ -/]*[@-~]', '', part)
            pieces.append('<span style="' + ';'.join(k+':'+v for k,v in style.items()) + '">' + html.escape(safe) + '</span>')
            continue
        codes = iter(int(c or 0) for c in part[2:-1].split(';'))
        for n in codes:
            if n == 0: style.clear()
            elif n == 1: style['font-weight'] = 'bold'
            elif n == 22: style.pop('font-weight', None)
            elif n == 7: style.update(color='#071828', **{'background-color':'#a7e0ff'})
            elif n == 27:
                style.pop('background-color', None)
                style.pop('color', None)
            elif n in (39,49): style.pop('color' if n == 39 else 'background-color', None)
            elif 30 <= n <= 37 or 90 <= n <= 97: style['color'] = COLORS[n % 10]
            elif 40 <= n <= 47 or 100 <= n <= 107: style['background-color'] = COLORS[n % 10]
            elif n in (38,48):
                mode = next(codes, None)
                if mode == 2:
                    rgb = [min(255,next(codes,0)) for _ in range(3)]
                    style['color' if n == 38 else 'background-color'] = '#%02x%02x%02x' % tuple(rgb)
                elif mode == 5: next(codes, None)
    return '<pre>' + ''.join(pieces) + '</pre>'


class ComponentView(QDialog):
    def __init__(self, data, parent):
        super().__init__(parent)
        self.key_value = ''
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Gentle Shell'))
        self.screen = QTextBrowser()
        self.screen.setOpenLinks(False)
        self.screen.setFocusPolicy(Qt.NoFocus)
        self.screen.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
        layout.addWidget(self.screen)
        self.update_frame(data.get('placeholder', ''))
        close = QPushButton('Cerrar panel'); close.setAutoDefault(False)
        close.setFocusPolicy(Qt.NoFocus); close.clicked.connect(self.reject)
        layout.addWidget(close)
        self.setFocusPolicy(Qt.StrongFocus)

    def update_frame(self, text):
        self.screen.setHtml(rich_frame(text))

    def keyPressEvent(self, event):
        keys = {Qt.Key_Up:'\x1b[A', Qt.Key_Down:'\x1b[B', Qt.Key_Right:'\x1b[C', Qt.Key_Left:'\x1b[D',
                Qt.Key_Escape:'\x1b', Qt.Key_Return:'\r', Qt.Key_Enter:'\r', Qt.Key_Tab:'\t',
                Qt.Key_Backtab:'\x1b[Z', Qt.Key_Backspace:'\x7f', Qt.Key_Delete:'\x1b[3~',
                Qt.Key_Home:'\x1b[H', Qt.Key_End:'\x1b[F', Qt.Key_PageUp:'\x1b[5~', Qt.Key_PageDown:'\x1b[6~'}
        value = keys.get(event.key(), event.text())
        if value:
            self.key_value = value
            event.accept()
            self.accept()

    def focusNextPrevChild(self, forward):
        return False

    def value(self):
        return self.key_value
