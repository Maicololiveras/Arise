"""In-flow, fixed-height public activity view; updates never take keyboard focus."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QTextEdit, QSizePolicy
from .activity import PublicActivity

class ActivityWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Fixed)
        self.setMinimumWidth(0)
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0);layout.setSpacing(2)
        self.toggle=QPushButton();self.toggle.setCheckable(True)
        self.toggle.setAccessibleName('Actividad de ARISE · mostrar u ocultar detalle')
        self.toggle.setFixedHeight(24);self.toggle.setMinimumWidth(0)
        self.toggle.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Fixed)
        self.toggle.setStyleSheet('text-align:left;padding:2px 5px;border:0;background:#10283C;color:#B9D0DF;font-size:11px;')
        layout.addWidget(self.toggle)
        self.summary=QLabel();self.summary.setFixedHeight(18);self.summary.setTextFormat(Qt.PlainText)
        self.summary.setStyleSheet('color:#9DB3C7;font-size:11px;');self.summary.setMinimumWidth(0)
        layout.addWidget(self.summary)
        self.details=QTextEdit();self.details.setReadOnly(True);self.details.setAcceptRichText(False)
        self.details.setFixedHeight(82);self.details.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.details.setStyleSheet('font-size:11px;padding:4px;background:#10283C;')
        layout.addWidget(self.details);self.details.hide()
        self.toggle.toggled.connect(self.expand)
        self.data=PublicActivity().snapshot();self.set_activity(self.data)
    def expand(self, expanded):
        self.details.setVisible(expanded);self.refresh_text()
    def set_activity(self, data):
        self.data=data
        model=data.get('model') or 'no informado'
        source='Modelo principal (respuesta)' if data.get('model_source')=='response' else 'Modelo principal (seleccionado)'
        lines=[f'{source}: {model}', 'Modelo de subagentes: no informado.',
               f"Herramientas terminadas: {data.get('tools_completed',0)} · Total no informado",
               f"Subagentes activos informados: {data.get('subagents_active',0)}"]
        lines.extend(reversed(data.get('details',[])[-30:]))
        text='\n'.join(lines)
        if text!=self.details.toPlainText():
            scroll=self.details.verticalScrollBar().value()
            self.details.setPlainText(text);self.details.verticalScrollBar().setValue(scroll)
        self.refresh_text()
    def refresh_text(self):
        d=self.data
        title=('▾' if self.toggle.isChecked() else '▸')+' Actividad de ARISE · '+d.get('label','Esperando')
        self.toggle.setText(self.toggle.fontMetrics().elidedText(title,Qt.ElideRight,max(40,self.width()-10)));self.toggle.setToolTip(title)
        full=(d.get('tool') or 'Sin herramienta activa informada')+f" · {d.get('tools_completed',0)} terminadas"
        if d.get('subagents_active'):full+=f" · {d['subagents_active']} subagente(s)"
        self.summary.setText(self.summary.fontMetrics().elidedText(full,Qt.ElideRight,max(40,self.width()-4)))
        self.summary.setToolTip(full)
    def resizeEvent(self,event):
        super().resizeEvent(event);self.refresh_text()
