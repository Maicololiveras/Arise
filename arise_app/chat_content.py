"""Bounded image attachments and native, selectable Markdown chat content."""
import base64
import html
import uuid
from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QImage, QTextCursor, QTextDocument, QTextDocumentFragment
from PySide6.QtWidgets import QTextBrowser

class ChatHistory(QTextBrowser):
    def __init__(self):
        super().__init__()
        self.entries = []
        self.rendered_language = None
        self.setOpenLinks(False)
        self.setOpenExternalLinks(False)
        self.document().setDefaultStyleSheet('''
            body { font-family: 'Segoe UI'; font-size: 15px; color: #EDF8FF; }
            p { margin-top: 8px; margin-bottom: 12px; line-height: 140%; }
            pre { background-color: #10283C; white-space: pre-wrap; }
            code { font-family: Consolas; color: #B4E7F2; }
            h1,h2,h3 { color: #EDF8FF; margin-top: 16px; }
            td,th { padding: 7px; border: 1px solid #365066; }
            a { color: #74D9FF; }
        ''')

    def loadResource(self, resource_type, url):
        # Model output cannot fetch remote images or read local files.
        return None

    def clear(self):
        self.entries = []
        super().clear()

    def retranslate(self):
        from .i18n import language
        if self.rendered_language == language(): return
        self.rendered_language = language()
        position=self.verticalScrollBar().value()
        super().clear()
        for role,text,images in self.entries: self.render_message(role,text,images)
        self.verticalScrollBar().setValue(position)

    def append_message(self, role, text, images=None):
        self.entries.append((role,text,images))
        self.render_message(role,text,images)

    def render_message(self, role, text, images=None):
        from .i18n import tr
        bar=self.verticalScrollBar(); follow=bar.value()>=bar.maximum()-24
        position=bar.value()
        cursor=QTextCursor(self.document());cursor.movePosition(QTextCursor.End)
        if not self.document().isEmpty(): cursor.insertBlock()
        cursor.insertHtml('<p><b style="color:#74F6FF">'+html.escape(tr(role))+'</b></p>')
        cursor.insertBlock()
        document=QTextDocument()
        if role in ('ARISE','Voz · ARISE'):
            document.setMarkdown(text,QTextDocument.MarkdownDialectGitHub|QTextDocument.MarkdownNoHTML)
        else: document.setPlainText(text)
        cursor.insertFragment(QTextDocumentFragment(document))
        for item in images or []:
            image=QImage.fromData(base64.b64decode(item['data']))
            if image.isNull(): continue
            image=image.scaled(280,180,Qt.KeepAspectRatio,Qt.SmoothTransformation)
            url=QUrl('arise-image:'+uuid.uuid4().hex)
            self.document().addResource(QTextDocument.ImageResource,url,image)
            cursor.insertBlock();cursor.insertImage(url.toString())
        cursor.insertBlock()
        bar.setValue(bar.maximum() if follow else position)
