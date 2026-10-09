import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import tempfile
import time
import unittest
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox, QTextEdit
from PySide6.QtCore import QTimer, Qt
from unittest.mock import patch
from PySide6.QtTest import QTest
from arise_app.assistant import Assistant
from arise_app.desktop import Controller, Settings
from arise_app.orb import build_orb

class NativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app=QApplication.instance() or QApplication([]);cls.app.setQuitOnLastWindowClosed(False)
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.r=Assistant(self.temp.name)
        self.app,self.orb=build_orb(self.app,96,20,20)
        self.c=Controller(self.app,self.r,self.orb,start_voice=False)
    def tearDown(self):
        self.c.close();self.orb.removeEventFilter(self.c);self.orb.close();self.c.panel.close()
        if self.c.settings_window:self.c.settings_window.close()
        self.r.storage.db.close();self.temp.cleanup()
    def test_compact_panel_orb_and_actual_state_updates(self):
        self.c.panel.show();QTest.qWait(100)
        self.assertLessEqual(self.c.panel.width(),440)
        self.assertLessEqual(self.c.panel.height(),550)
        self.assertEqual(self.orb.width(),96)
        self.r.orb.update("waiting_approval",microphone=True,control=True)
        self.c.poll();QTest.qWait(30)
        self.assertIn("TU DECISIÓN",self.c.panel.status.text())
        self.assertIn("Control activo",self.c.panel.privacy.text())
        self.orb.grab().save(str(Path(self.temp.name)/"orb.png"))
    def test_settings_save_and_clamp_position(self):
        settings=Settings(self.c)
        settings.fields["orb_size"].setValue(80)
        settings.fields["pinned"].setChecked(True)
        self.assertTrue(settings.save(),settings.message.text())
        QTest.qWait(30);self.assertEqual(self.orb.width(),80)
        self.orb.move(-10000,-10000);self.c.clamp_position()
        self.assertGreaterEqual(self.orb.x(),self.app.primaryScreen().availableGeometry().left())
        settings.close()
    def test_closing_orb_keeps_application_services_alive(self):
        self.orb.close();QTest.qWait(30)
        self.assertFalse(self.orb.isVisible())
        self.r.call_tool("memory.save",{"text":"Después de cerrar orbe"})
        self.assertTrue(self.r.memory_path.exists())
        self.assertFalse(self.c.closed)

    def test_enter_sends_shift_enter_adds_line_and_chat_has_space(self):
        panel = self.c.panel; panel.show(); QTest.qWait(30)
        self.assertGreater(panel.history.height(), 300)
        sent = []
        with patch.object(self.r, "steer", side_effect=lambda text:sent.append(text)):
            panel.input.setFocus(); QTest.keyClicks(panel.input, "hola")
            QTest.keyClick(panel.input, Qt.Key_Return, Qt.ShiftModifier)
            self.assertEqual(panel.input.toPlainText(), "hola\n")
            QTest.keyClicks(panel.input, "arise"); QTest.keyClick(panel.input, Qt.Key_Return)
            QTest.qWait(80)
            self.assertEqual(sent, ["hola\narise"])
            self.assertEqual(panel.input.toPlainText(), "")
        self.assertEqual(panel.mic_button.toolTip(), "Hablar con ARISE")
        self.assertEqual(panel.windowTitle(), "ARISE Assistant")

    def test_rpc_editor_returns_multiline_text_and_chat_change_closes_dialog(self):
        answers=[]
        with patch.object(self.r,'answer_dialog',side_effect=lambda record:answers.append(record)):
            self.c.dialog({'id':'edit-fixture','method':'editor','title':'Perfil JSON','prefill':'uno\ndos'})
            dialog=self.c.pending_dialogs['edit-fixture']; dialog.findChild(QTextEdit).setPlainText('modelo\nesfuerzo')
            dialog.accept(); QTest.qWait(80)
            self.assertEqual(answers[0]['value'],'modelo\nesfuerzo')
            self.assertFalse(answers[0]['cancelled'])
            self.c.dialog({'id':'old-chat','method':'input','title':'Perfil'})
            self.c.close_dialogs(); QTest.qWait(30)
            self.assertFalse(self.c.pending_dialogs)
            self.assertEqual(len(answers),1)
