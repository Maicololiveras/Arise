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
        self.assertTrue(self.orb.isVisible())
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

    def test_double_click_opens_single_click_hides_without_voice(self):
        self.assertFalse(self.c.panel.isVisible())
        with patch.object(self.c.voice, 'wake') as wake:
            QTest.mouseDClick(self.orb, Qt.LeftButton); QTest.mouseRelease(self.orb, Qt.LeftButton); QTest.qWait(20)
            self.assertTrue(self.c.panel.isVisible())
            QTest.mouseClick(self.orb, Qt.LeftButton); QTest.qWait(20)
            self.assertFalse(self.c.panel.isVisible()); self.assertTrue(self.orb.isVisible()); wake.assert_not_called()

    def test_panel_follows_orb_position_is_saved_and_offscreen_is_clamped(self):
        self.c.show_panel(); self.orb.move(400, 30); QTest.qWait(350)
        self.assertEqual(self.r.storage.config['orb_position'], [400, 30])
        self.assertEqual(self.c.panel.x(), self.orb.x()-self.c.panel.width()-12)
        self.assertEqual(self.c.panel.y(), 30)
        self.orb.move(-10000,-10000); QTest.qWait(350)
        self.assertGreaterEqual(self.orb.x(), 0); self.assertGreaterEqual(self.c.panel.x(), 0)
        self.assertEqual(self.r.storage.config['orb_position'], [self.orb.x(), self.orb.y()])

    def test_idle_hides_chat_after_minute_and_typing_resets_timer(self):
        self.c.show_panel(); self.c.last_interaction=time.monotonic()-59
        self.c.hide_if_idle(); self.assertTrue(self.c.panel.isVisible())
        QTest.keyClicks(self.c.panel.input,'borrador')
        self.assertLess(time.monotonic()-self.c.last_interaction,1)
        self.c.last_interaction=time.monotonic()-61; self.c.hide_if_idle()
        self.assertFalse(self.c.panel.isVisible()); self.assertTrue(self.orb.isVisible())
        self.c.show_panel(); self.assertEqual(self.c.panel.input.toPlainText(),'borrador')

    def test_unpinned_legacy_config_cannot_hide_persistent_orb(self):
        self.r.storage.config['pinned']=False; self.c.reconfigure()
        self.r.orb.update('idle'); self.c.poll()
        self.assertTrue(self.orb.isVisible())

    def test_voice_wake_does_not_open_chat(self):
        with patch.object(self.c.voice,'wake',return_value=True) as wake:
            self.c.wake('hola');QTest.qWait(50)
            self.assertFalse(self.c.panel.isVisible());self.assertTrue(self.orb.isVisible())
            wake.assert_called_once_with('hola')
