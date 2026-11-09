"""Provider sign-in inside Settings; never a terminal or embedded password browser."""
import threading
import uuid
from PySide6.QtCore import Qt, QTimer, QUrl, QObject, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QPushButton,QLineEdit,QScrollArea,QWidget,QMessageBox)


class Request(QObject):
    done=Signal(object)
    failed=Signal(str)


class AccountsDialog(QDialog):
    def __init__(self,runtime,parent=None):
        super().__init__(parent)
        self.runtime=runtime;self.owner=uuid.uuid4().hex;self.closed=False;self.jobs=[];self.polling=False;self.flow=False;self.prompt_id=None;self.url='';self.opened=set()
        self.setWindowTitle('ARISE · Cuentas del agente');self.resize(540,570)
        self.setMinimumSize(300,300)
        layout=QVBoxLayout(self);scroll=QScrollArea();scroll.setWidgetResizable(True);layout.addWidget(scroll)
        content=QWidget();scroll.setWidget(content);body=QVBoxLayout(content)
        help=QLabel('Conecta tu cuenta sin abrir una terminal. La autorización se realiza en la página oficial del proveedor y vuelve a ARISE.');help.setWordWrap(True);body.addWidget(help)
        self.providers=QComboBox();self.providers.setAccessibleName('Proveedor de la cuenta');body.addWidget(self.providers)
        self.methods=QComboBox();self.methods.setAccessibleName('Método de acceso');body.addWidget(self.methods)
        self.state=QLabel('Cargando cuentas…');self.state.setWordWrap(True);self.state.setTextFormat(Qt.PlainText);body.addWidget(self.state)
        row=QHBoxLayout();self.connect=QPushButton('Conectar');self.logout=QPushButton('Desconectar');row.addWidget(self.connect);row.addWidget(self.logout);body.addLayout(row)
        self.notice=QLabel();self.notice.setWordWrap(True);self.notice.setTextFormat(Qt.PlainText);self.notice.setTextInteractionFlags(Qt.TextSelectableByMouse);body.addWidget(self.notice)
        self.browser=QPushButton('Abrir página de autorización');self.browser.hide();body.addWidget(self.browser)
        self.prompt=QLabel();self.prompt.setWordWrap(True);self.prompt.setTextFormat(Qt.PlainText);body.addWidget(self.prompt)
        self.answer=QLineEdit();self.answer.setEchoMode(QLineEdit.Password);self.answer.setAccessibleName('Clave o código de autorización');self.answer.hide();body.addWidget(self.answer)
        self.options=QComboBox();self.options.hide();body.addWidget(self.options)
        self.submit=QPushButton('Continuar');self.submit.hide();body.addWidget(self.submit)
        self.models=QComboBox();self.models.setAccessibleName('Modelo para este chat');body.addWidget(self.models)
        self.select=QPushButton('Usar este modelo en el chat');self.select.setEnabled(False);body.addWidget(self.select)
        body.addStretch()
        footer=QHBoxLayout();self.cancel=QPushButton('Cancelar acceso');self.cancel.setEnabled(False);close=QPushButton('Cerrar');footer.addWidget(self.cancel);footer.addWidget(close);layout.addLayout(footer)
        self.connect.clicked.connect(self.start);self.logout.clicked.connect(self.disconnect_account)
        self.providers.currentIndexChanged.connect(self.provider_changed);self.browser.clicked.connect(self.open_browser)
        self.submit.clicked.connect(self.respond);self.answer.returnPressed.connect(self.respond);self.cancel.clicked.connect(self.cancel_flow);close.clicked.connect(self.reject)
        self.select.clicked.connect(self.select_model)
        self.timer=QTimer(self);self.timer.setInterval(500);self.timer.timeout.connect(self.poll)
        self.load()

    def call(self,action,**data):
        body={'owner':self.owner,**data}
        if getattr(self.runtime,'is_remote',False):return self.runtime.provider_account(action,body)
        return self.runtime.accounts.call(action,body)

    def run(self,action,done,**data):
        worker=Request();self.jobs.append(worker)
        def finish(value):
            if not self.closed:done(value)
            self.jobs.remove(worker);worker.deleteLater()
        def failure(message):
            self.polling=False
            if not self.closed:
                self.state.setText(message);self.connect.setEnabled(True)
                if action in ('start','status','answer','cancel'):
                    self.flow=False;self.timer.stop();self.providers.setEnabled(True);self.methods.setEnabled(True);self.cancel.setEnabled(False)
                    self.answer.clear();self.answer.hide();self.submit.hide();self.options.hide()
            self.jobs.remove(worker);worker.deleteLater()
        worker.done.connect(finish);worker.failed.connect(failure)
        def task():
            try:
                result=self.call(action,**data)
                if self.closed:self.call('close')
                worker.done.emit(result)
            except Exception as error:worker.failed.emit(str(error))
        threading.Thread(target=task,daemon=True).start()

    def load(self):
        self.connect.setEnabled(False)
        self.run('providers',self.loaded)

    def loaded(self,result):
        selected=self.providers.currentData()
        self.records=result['providers'];self.providers.blockSignals(True);self.providers.clear()
        for p in self.records:self.providers.addItem(p['name'],p['id'])
        i=self.providers.findData(selected or self.runtime.storage.config.get('agent_provider') or 'openai')
        self.providers.setCurrentIndex(max(i,0));self.providers.blockSignals(False);self.provider_changed()

    def provider_changed(self):
        provider=next((p for p in getattr(self,'records',[]) if p['id']==self.providers.currentData()),None)
        if not provider:return
        self.methods.clear()
        for method in provider['methods']:self.methods.addItem(provider.get('oauthName') or 'Iniciar sesión' if method=='oauth' else 'Clave API',method)
        connected=provider.get('configured',False)
        self.state.setText(('Cuenta configurada' if connected else 'Sin cuenta conectada')+(' · credencial del entorno; desconectar aquí no elimina su origen' if provider.get('source') in ('environment','runtime','config') else ''))
        self.connect.setEnabled(True);self.logout.setEnabled(connected);self.models.clear();self.select.setEnabled(False)
        selected=provider['id']
        if connected:self.run('models',lambda result:self.show_models(result) if self.providers.currentData()==selected else None,provider=selected)

    def show_models(self,result):
        self.models.clear()
        for model in result['models']:self.models.addItem(model.get('name') or model['id'],model)
        self.select.setEnabled(self.models.count()>0)

    def start(self):
        self.connect.setEnabled(False);self.providers.setEnabled(False);self.methods.setEnabled(False);self.logout.setEnabled(False);self.select.setEnabled(False)
        self.notice.clear();self.opened.clear();self.browser.hide();self.flow=True;self.cancel.setEnabled(True)
        self.run('start',self.update_flow,provider=self.providers.currentData(),method=self.methods.currentData());self.timer.start()

    def poll(self):
        if self.polling or not self.flow:return
        self.polling=True;self.run('status',self.update_flow)

    def update_flow(self,result):
        self.polling=False;state=result.get('state');self.state.setText({'waiting':'Esperando autorización…','prompt':'Completa el acceso','done':'Cuenta conectada. Elige un modelo.','error':'No se pudo conectar. Puedes intentarlo de nuevo.','cancelled':'Acceso cancelado.'}.get(state,'Preparando acceso…'))
        note=result.get('notice',{})
        if note:
            self.notice.setText(note.get('message','')+('\nCódigo: '+note['code'] if note.get('code') else ''))
            if note.get('url'):
                self.url=note['url'];self.browser.show()
                if self.url not in self.opened:self.opened.add(self.url);self.open_browser()
        prompt=result.get('prompt')
        if prompt and prompt['id']!=self.prompt_id:
            self.prompt_id=prompt['id'];self.prompt.setText(prompt.get('message',''));self.answer.clear();self.options.clear()
            is_select=prompt['kind']=='select';self.answer.setVisible(not is_select);self.options.setVisible(is_select)
            for option in prompt.get('options') or []:self.options.addItem(option['label'],option['id'])
            self.submit.show();self.submit.setEnabled(True);self.answer.setFocus()
        if state in ('done','error','cancelled'):
            self.flow=False;self.timer.stop();self.cancel.setEnabled(False);self.providers.setEnabled(True);self.methods.setEnabled(True);self.connect.setEnabled(True)
            self.answer.clear();self.answer.hide();self.options.hide();self.submit.hide();self.prompt.clear();self.prompt_id=None;self.browser.hide();self.notice.setText(result.get('message') or ('Acceso completado.' if state=='done' else 'Acceso cancelado.' if state=='cancelled' else 'No se pudo completar el acceso.'))
            self.load()

    def open_browser(self):
        url=QUrl(self.url)
        if url.scheme()=='https' and not url.userInfo():QDesktopServices.openUrl(url)

    def respond(self):
        if not self.prompt_id:return
        value=self.options.currentData() if self.options.isVisible() else self.answer.text()
        self.answer.clear();self.submit.setEnabled(False);self.answer.hide();self.options.hide()
        self.run('answer',self.update_flow,prompt_id=self.prompt_id,value=value or '')

    def cancel_flow(self):
        self.timer.stop();self.flow=False;self.run('cancel',self.update_flow)

    def disconnect_account(self):
        if QMessageBox.question(self,'Desconectar cuenta','¿Eliminar de ARISE la credencial guardada de esta cuenta?')==QMessageBox.Yes:
            self.run('logout',self.loaded,provider=self.providers.currentData())

    def select_model(self):
        model=self.models.currentData()
        if model:self.run('select_model',lambda _:self.state.setText('Modelo seleccionado para este chat.'),provider=model['provider'],model=model['id'])

    def done(self,result):
        self.closed=True;self.flow=False;self.timer.stop();self.answer.clear();self.notice.clear()
        def close_account():
            try:self.call('close')
            except Exception:pass
        threading.Thread(target=close_account,daemon=True).start()
        super().done(result)
