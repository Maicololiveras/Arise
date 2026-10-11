import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile
import unittest
from unittest.mock import Mock
from PySide6.QtWidgets import QApplication,QPushButton
from arise_app.assistant import Assistant
from arise_app.desktop import Settings

class DownloadSettingsTests(unittest.TestCase):
    def test_individual_buttons_send_selection_and_recover_from_error(self):
        app=QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as root:
            runtime=Assistant(root);runtime.is_remote=True;runtime.request=Mock(return_value={})
            controller=Mock(runtime=runtime);window=Settings(controller);window.save=Mock(return_value=True)
            try:
                for prefix,endpoint,component in [('Descargar Whisper','models/download','whisper'),('Descargar / reparar ScreenView','tools/setup-desktop','screenview')]:
                    button=next(b for b in window.findChildren(QPushButton) if b.text().startswith(prefix))
                    button.click();app.processEvents()
                    operation,success,failure=controller.background.call_args.args
                    self.assertFalse(window.isEnabled())
                    operation()
                    self.assertEqual(runtime.request.call_args.args[:2],(endpoint,{'components':[component]}))
                    failure('fallo de descarga')
                    self.assertTrue(window.isEnabled())
                    self.assertIn('fallo de descarga',window.message.text())
            finally:window.close();runtime.close()
