import base64
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile
import unittest
from unittest.mock import patch, Mock
from PySide6.QtCore import QMimeData, QBuffer, QIODevice, Qt
from PySide6.QtGui import QImage, QTextDocument
from PySide6.QtWidgets import QApplication
from arise_app.attachments import validate_images
from arise_app.desktop import ChatInput
from arise_app.chat_content import ChatHistory
from arise_app.assistant import Assistant
from arise_app.storage import Storage

class ChatImagesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def image(self):
        image=QImage(40,30,QImage.Format_RGB32);image.fill(Qt.cyan)
        buffer=QBuffer();buffer.open(QIODevice.WriteOnly);image.save(buffer,'PNG')
        return image,{'type':'image','mimeType':'image/png','data':base64.b64encode(bytes(buffer.data())).decode()}
    def test_clipboard_image_signal_and_plain_text_paste(self):
        editor=ChatInput();received=[];editor.image_pasted.connect(received.append)
        mime=QMimeData();mime.setImageData(self.image()[0]);editor.insertFromMimeData(mime)
        self.assertEqual(len(received),1);self.assertEqual(received[0].size(),self.image()[0].size())
        mime=QMimeData();mime.setText('Mensaje');editor.insertFromMimeData(mime)
        self.assertEqual(editor.toPlainText(),'Mensaje')
    def test_markdown_and_images_render_without_external_resources(self):
        history=ChatHistory();image,payload=self.image()
        history.append_message('ARISE','## Resultado\n\n**Correcto**\n\n- Uno\n- Dos\n\n```python\nprint(1)\n```',[payload])
        plain=history.toPlainText();self.assertIn('Resultado',plain);self.assertNotIn('**',plain);self.assertNotIn('```',plain)
        html=history.toHtml();self.assertIn('<img',html);self.assertIn('font-weight:700',html)
        self.assertIsNone(history.loadResource(QTextDocument.ImageResource,'file:///private'))
    def test_image_reaches_prompt_and_survives_storage_reopen(self):
        with tempfile.TemporaryDirectory() as root:
            runtime=Assistant(root);payload=self.image()[1]
            process=Mock();process.request.return_value={'data':{}}
            runtime.pi=process;runtime.pi_state={}
            with patch.object(runtime,'connect_pi'):
                runtime.prompt('Mira esto',[payload])
            prompt=process.request.call_args_list[0].args[0]
            self.assertEqual(prompt['images'],[payload])
            runtime.busy=True;runtime.steer('Otra imagen',[payload])
            self.assertEqual(process.request.call_args.args[0]['images'],[payload])
            chat=runtime.conversation;runtime.storage.db.close()
            storage=Storage(root);messages=storage.messages(chat)
            self.assertEqual(messages[-1]['images'],[payload]);storage.db.close()
    def test_rejects_oversized_or_invalid_image_payloads(self):
        payload=self.image()[1]
        for invalid in ([payload]*5,[{**payload,'data':'invalid!'}],[{**payload,'mimeType':'image/svg+xml'}],[{**payload,'data':'A'*3000000}]):
            with self.assertRaises(ValueError):validate_images(invalid)
