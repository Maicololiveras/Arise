"""Integration checks for the native renderer on Qt-enabled runners."""
import importlib.util
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

@unittest.skipUnless(importlib.util.find_spec("PySide6"),"requires native Qt")
class DesktopStreamUiTests(unittest.TestCase):
    def test_complete_stream_and_one_final_message(self):
        from PySide6.QtWidgets import QApplication
        from arise_app.assistant import Assistant
        from arise_app.desktop import Controller
        from arise_app.orb import build_orb
        app=QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as root:
            rt=Assistant(root);app,orb=build_orb(app,96,20,20)
            ui=Controller(app,rt,orb,start_voice=False)
            try:
                message="Long response "+("x"*1500)
                rt.pi_event({"type":"message_start","message":{"role":"assistant"}})
                for chunk in (message[:800],message[800:]):
                    rt.pi_event({"type":"message_update","assistantMessageEvent":{"type":"text_delta","delta":chunk}})
                ui.poll()
                self.assertEqual(ui.panel.live_reply.toPlainText(),message)
                rt.pi_event({"type":"message_end","message":{"role":"assistant","content":[{"type":"text","text":message}]}})
                ui.poll()
                self.assertEqual(ui.panel.live_reply.toPlainText(),"")
                self.assertEqual(ui.panel.history.toPlainText().count(message),1)
            finally:
                ui.close();orb.close();ui.panel.close();app.processEvents();rt.storage.db.close()
