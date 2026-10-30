"""Desktop-only connection controls; secrets never enter the mobile API."""
import json
from pathlib import Path
from PySide6.QtCore import QThread, Signal, Qt, QUrl
from PySide6.QtGui import QImage, QPixmap, QDesktopServices
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLabel, QLineEdit,
    QApplication, QPushButton, QTabWidget, QWidget, QScrollArea, QTextEdit, QListWidget, QListWidgetItem)


class RequestWorker(QThread):
    result = Signal(object)
    error = Signal(str)
    def __init__(self, function, parent):
        super().__init__(parent); self.function = function
    def run(self):
        try: self.result.emit(self.function())
        except Exception as error: self.error.emit(str(error)[:400])


class ConnectionsDialog(QDialog):
    def __init__(self, runtime, parent=None):
        super().__init__(parent)
        self.runtime = runtime
        self.worker = None
        self.setModal(True)
        self.setWindowTitle('ARISE · Conexiones y recordatorios · QA')
        self.resize(620, 650)
        layout = QVBoxLayout(self)
        intro = QLabel('Autoriza cada cuenta y destinatario. Las tareas se ejecutan en el PC; conectar un servicio no habilita ejecución local ni control del escritorio.')
        intro.setWordWrap(True); layout.addWidget(intro)
        self.tabs = QTabWidget(); layout.addWidget(self.tabs)
        self.status = QLabel('Conexiones de salida para recordatorios. Recepción de mensajes de Telegram, WhatsApp y Teams pendiente.')
        self.status.setWordWrap(True); layout.addWidget(self.status)
        self.output = QTextEdit(); self.output.setReadOnly(True); self.output.setMaximumHeight(150); layout.addWidget(self.output)
        self.fields = {}
        for provider in ('telegram','whatsapp','outlook','teams'):
            form = self.page(provider.title())
            if provider in ('outlook','teams'):
                field = self.field(form,'Application (client) ID de Entra')
                self.button(form,'1 · Iniciar conexión Microsoft',lambda p=provider,f=field:self.run('connections/oauth/start',{'provider':p,'client_id':f.text().strip()}))
                self.button(form,'2 · Comprobar después de autorizar',lambda p=provider:self.run('connections/oauth/poll',{'provider':p}))
                hint = QLabel('La aplicación Entra debe admitir clientes públicos. Outlook solicita Mail.Send; Teams solicita ChatMessage.Send para una cuenta organizacional. La renovación queda protegida en Windows.')
                hint.setWordWrap(True); form.addRow(hint)
            else:
                token = self.field(form,'Token del bot / cuenta',secret=True)
                options = {}
                if provider == 'whatsapp':
                    for key,label in [('phone_id','Phone Number ID'),('api_version','Versión Graph API (vN.N)'),('template','Nombre de plantilla aprobada'),('language','Idioma (ej. es_CO)')]: options[key]=self.field(form,label)
                    hint=QLabel('La plantilla debe tener una variable de cuerpo para el recordatorio. Requiere WhatsApp Business Platform y consentimiento del destinatario.');hint.setWordWrap(True);form.addRow(hint)
                self.button(form,'Guardar credencial en Windows',lambda p=provider,t=token,o=options:self.save_token(p,t,o))
            self.button(form,'Desconectar cuenta',lambda p=provider:self.run('connections/disconnect',{'provider':p}))
        mobile = self.page('Celular')
        self.android_download(mobile)
        hint=QLabel('Instala Tailscale en el PC y el teléfono e inicia sesión. Después configura tu autenticador y vincula el chat. El PC debe permanecer encendido.')
        hint.setWordWrap(True);mobile.addRow(hint)
        self.pair_qr=QLabel();self.pair_qr.setAlignment(Qt.AlignCenter);mobile.addRow(self.pair_qr)
        self.button(mobile,'1 · Configurar verificación en dos pasos',lambda:self.run('mobile/security/begin',{},self.show_mobile_qr))
        otp=self.field(mobile,'Código de seis dígitos del autenticador',secret=True)
        otp.setMaxLength(6)
        def confirmed(value):
            otp.clear();self.pair_qr.clear();self.output.clear()
            self.status.setText('Autenticador confirmado. Espera su siguiente código para vincular el teléfono.')
        self.button(mobile,'Confirmar autenticador',lambda:self.run('mobile/security/confirm',{'code':otp.text().strip()},confirmed))
        self.button(mobile,'2 · Preparar conexión privada automáticamente',lambda:self.run('mobile/prepare',{}))
        self.button(mobile,'3 · Vincular este chat con mi teléfono',lambda:self.run('mobile/link',{},self.show_mobile_qr))
        self.devices=QListWidget();self.devices.setMinimumHeight(90);mobile.addRow(self.devices)
        self.button(mobile,'Actualizar dispositivos',self.refresh_devices)
        self.button(mobile,'Revocar dispositivo seleccionado',self.revoke)
        self.button(mobile,'Detener acceso móvil',lambda:self.run('mobile/stop',{}))
        jobs=self.page('Recordatorios')
        label=QLabel('Pide en el chat: «Recuérdame mañana a las 9:00, hora de Colombia…». Confirma la fecha y el destino en el PC. Si está apagado, se entregará al reabrir ARISE. Detener una tarea no cancela sus recordatorios.');label.setWordWrap(True);jobs.addRow(label)
        self.jobs=QListWidget();self.jobs.setMinimumHeight(150);jobs.addRow(self.jobs)
        self.button(jobs,'Actualizar recordatorios',self.refresh_jobs)
        self.button(jobs,'Cancelar seleccionado',self.cancel_job)
        close=QPushButton('Cerrar');close.clicked.connect(self.close);layout.addWidget(close)

    def show_mobile_qr(self, value):
        import qrcode
        url=value.get('uri') or value.get('url')
        matrix=qrcode.QRCode(border=4);matrix.add_data(url);matrix.make(fit=True)
        cells=matrix.get_matrix();size=len(cells)
        image=QImage(size,size,QImage.Format_RGB32);image.fill(Qt.white)
        for y,row in enumerate(cells):
            for x,dark in enumerate(row):
                if dark:image.setPixelColor(x,y,Qt.black)
        self.pair_qr.setPixmap(QPixmap.fromImage(image).scaled(280,280,Qt.KeepAspectRatio,Qt.FastTransformation))
        self.status.setText('Escanea con tu autenticador y confirma el código.' if 'uri' in value else 'Escanea con la cámara del teléfono. También puedes pegar el enlace en ARISE Android. Vence en cinco minutos.')
        self.output.setPlainText(value.get('secret') or url)

    def android_download(self, form):
        data = json.loads((Path(__file__).parent/'resources/android-download-qr.json').read_text())
        url = data['url']
        title = QLabel('1 · Descargar ARISE para Android · QA')
        title.setWordWrap(True); form.addRow(title)
        matrix = data['matrix']; size = len(matrix)
        image = QImage(size, size, QImage.Format_RGB32)
        image.fill(Qt.white)
        for y, row in enumerate(matrix):
            for x, dark in enumerate(row):
                if dark: image.setPixelColor(x, y, Qt.black)
        qr = QLabel(); qr.setObjectName('androidDownloadQr')
        qr.setAccessibleName('QR para descargar ARISE Android QA desde GitHub')
        qr.setToolTip(url)
        qr.setPixmap(QPixmap.fromImage(image).scaled(size*4, size*4, Qt.KeepAspectRatio, Qt.FastTransformation))
        qr.setAlignment(Qt.AlignCenter); form.addRow(qr)
        hint = QLabel('Escanea con tu Android y descarga ARISE-Android-QA.apk en Assets. '
                      'Es una versión de prueba; Android solicitará autorizar la instalación. '
                      'Este QR no vincula el celular ni concede permisos al PC. '
                      'En iPad utiliza el acceso web privado; el APK es solo para Android.')
        hint.setWordWrap(True); form.addRow(hint)
        self.button(form, 'Abrir descarga Android', lambda: QDesktopServices.openUrl(QUrl(url)))
        def copy():
            QApplication.clipboard().setText(url)
            self.status.setText('Enlace de descarga Android copiado. No contiene un código de vinculación.')
        self.button(form, 'Copiar enlace de descarga', copy)
        label = QLabel('2 · Vincular el celular con este PC')
        label.setWordWrap(True); form.addRow(label)

    def page(self,title):
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        panel=QWidget();form=QFormLayout(panel);form.setRowWrapPolicy(QFormLayout.WrapAllRows)
        scroll.setWidget(panel);self.tabs.addTab(scroll,title);return form

    def field(self,form,label,secret=False):
        field=QLineEdit();field.setAccessibleName(label)
        if secret:field.setEchoMode(QLineEdit.Password)
        form.addRow(label,field);return field

    def button(self,form,label,callback):
        button=QPushButton(label);button.clicked.connect(callback);form.addRow(button)

    def request(self,path,data):
        if getattr(self.runtime,'is_remote',False):return self.runtime.request(path,data)
        r=self.runtime
        methods={'connections/oauth/start':r.connections.oauth_start,'connections/oauth/poll':r.connections.oauth_poll,
                 'connections/disconnect':r.connections.disconnect,'mobile/start':r.start_mobile,'mobile/stop':r.stop_mobile}
        if path in methods:return methods[path](**(data or {}))
        if path=='connections/token':return r.connections.save_token(data['provider'],data['token'],**data['options'])
        if path=='mobile/prepare':
            from .mobile_setup import prepare
            return prepare(r)
        if path=='mobile/link':
            from .mobile_setup import invite
            return invite(r)
        if path=='mobile/security/begin':return r.mobile_security.begin()
        if path=='mobile/security/confirm':return r.mobile_security.confirm(data.get('code'))
        if path=='mobile/invite':return r.devices.invite(r.conversation)
        if path=='mobile/devices':return {'devices':r.devices.list(r.conversation)}
        if path=='mobile/revoke':return r.devices.revoke(r.conversation,data['id'])
        if path=='reminders':return {'reminders':r.reminders.list(r.conversation)}
        if path=='reminders/cancel':return r.reminders.cancel(r.conversation,data['id'])
        raise ValueError('Operación desconocida.')

    def run(self,path,data=None,callback=None):
        if self.worker and self.worker.isRunning():return
        self.tabs.setEnabled(False);self.status.setText('Procesando en el PC…')
        self.worker=RequestWorker(lambda:self.request(path,data),self)
        def done(value):
            self.status.setText('Operación terminada. Configurado no significa verificado con una entrega real.')
            self.output.setPlainText(json.dumps(value,ensure_ascii=False,indent=2))
            if callback:callback(value)
        self.worker.result.connect(done);self.worker.error.connect(self.status.setText)
        self.worker.finished.connect(lambda:self.tabs.setEnabled(True));self.worker.start()

    def save_token(self,provider,field,options):
        self.run('connections/token',{'provider':provider,'token':field.text().strip(),'options':{k:v.text().strip() for k,v in options.items()}},lambda _:field.clear())

    def refresh_devices(self):
        def fill(value):
            self.devices.clear()
            for row in value['devices']:
                item=QListWidgetItem(row['name']+(' · Revocado' if row['revoked'] else ' · Registrado'));item.setData(Qt.UserRole,row['id']);self.devices.addItem(item)
        self.run('mobile/devices',callback=fill)

    def revoke(self):
        item=self.devices.currentItem()
        if item:self.run('mobile/revoke',{'id':item.data(Qt.UserRole)})

    def refresh_jobs(self):
        def fill(value):
            self.jobs.clear()
            for row in value['reminders']:
                item=QListWidgetItem(f"{row['status']} · {row['at']} · {row['text']}");item.setData(Qt.UserRole,row['id']);self.jobs.addItem(item)
        self.run('reminders',callback=fill)

    def cancel_job(self):
        item=self.jobs.currentItem()
        if item:self.run('reminders/cancel',{'id':item.data(Qt.UserRole)})

    def closeEvent(self,event):
        if self.worker and self.worker.isRunning():event.ignore();return
        self.output.clear();super().closeEvent(event)
