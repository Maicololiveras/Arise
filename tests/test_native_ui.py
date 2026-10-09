import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import tempfile
import time
import unittest
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer
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
