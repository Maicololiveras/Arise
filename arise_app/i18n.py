"""Bundled Spanish/English UI catalog. No network translation or user-text rewriting."""
import json
from pathlib import Path

CATALOG = json.loads((Path(__file__).parent/'resources/i18n/en.json').read_text(encoding='utf-8'))
_language = 'es'


def language(): return _language


def set_language(value):
    global _language
    if value not in ('es', 'en'): raise ValueError('Unsupported interface language')
    _language = value


def tr(text, locale=None):
    if (locale or _language) != 'en' or not isinstance(text, str): return text
    if text in CATALOG: return CATALOG[text]
    if '\n' in text: return '\n'.join(tr(line, locale) for line in text.split('\n'))
    for prefix in ('✓ ', '○ ', '⚠ '):
        if text.startswith(prefix): return prefix + tr(text[len(prefix):], locale)
    # Only explicit UI fragments; paths, credentials and model identifiers are never parsed.
    for source in sorted((k for k in CATALOG if k.endswith(' ') and len(k.strip()) > 2), key=len, reverse=True):
        if text.startswith(source): return CATALOG[source]+tr(text[len(source):],locale)
    if ' · ' in text: return ' · '.join(tr(part, locale) for part in text.split(' · '))
    return text


class LiveTranslator:
    """Refresh presentation properties while preserving editors and semantic item values."""
    def __init__(self, app, locale='es'):
        import weakref
        from PySide6.QtCore import QObject, QEvent, QTimer
        self.app = app
        self.sources = weakref.WeakKeyDictionary()
        self.refreshing = False
        owner = self
        class Filter(QObject):
            def eventFilter(self, obj, event):
                if event.type() in (QEvent.Show, QEvent.Polish): owner.refresh_widget(obj)
                return False
        self.filter = Filter(app); app.installEventFilter(self.filter)
        self.timer = QTimer(self.filter); self.timer.setInterval(150)
        self.timer.timeout.connect(self.refresh);self.timer.start()
        self.set_language(locale)

    def set_language(self, locale):
        set_language(locale)
        self.refresh()

    def field(self, obj, key, getter, setter):
        from PySide6.QtCore import QSignalBlocker
        current = getter()
        if not isinstance(current,str) or not current: return
        values = self.sources.setdefault(obj,{})
        original, rendered = values.get(key,(current,current))
        if current != rendered: original = current
        value = tr(original)
        if value != current:
            blocker = QSignalBlocker(obj)
            setter(value)
            del blocker
        values[key] = (original,value)

    def refresh_widget(self, obj):
        from PySide6.QtWidgets import QWidget, QLabel, QAbstractButton, QLineEdit, QTextEdit, QPlainTextEdit, QTabWidget, QComboBox
        from PySide6.QtGui import QAction
        if isinstance(obj,QWidget):
            for key in ('windowTitle','toolTip','accessibleName','accessibleDescription'):
                self.field(obj,key,getattr(obj,key),getattr(obj,'set'+key[0].upper()+key[1:]))
            if isinstance(obj,(QLabel,QAbstractButton)) and not obj.property('userContent'):
                self.field(obj,'text',obj.text,obj.setText)
            if isinstance(obj,(QLineEdit,QTextEdit,QPlainTextEdit)):
                self.field(obj,'placeholder',obj.placeholderText,obj.setPlaceholderText)
            if isinstance(obj,QTabWidget):
                for index in range(obj.count()):
                    self.field(obj,('tab',index),lambda i=index:obj.tabText(i),lambda value,i=index:obj.setTabText(i,value))
            if isinstance(obj,QComboBox) and obj.property('localizedItems'):
                for index in range(obj.count()):
                    self.field(obj,('item',index),lambda i=index:obj.itemText(i),lambda value,i=index:obj.setItemText(i,value))
            for action in obj.actions(): self.refresh_widget(action)
        elif isinstance(obj,QAction):
            self.field(obj,'tooltip',obj.toolTip,obj.setToolTip)
            self.field(obj,'text',obj.text,obj.setText)

    def refresh(self):
        if self.refreshing: return
        self.refreshing = True
        try:
            for widget in self.app.allWidgets():
                self.refresh_widget(widget)
                if hasattr(widget,'retranslate'): widget.retranslate()
        finally: self.refreshing = False

    def close(self):
        self.timer.stop(); self.app.removeEventFilter(self.filter)
