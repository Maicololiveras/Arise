"""Native Qt interaction tests with an actual subprocess and simulated audio.

These verify draft/lifecycle safety, not speech accuracy or microphone hardware.
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from arise_app.assistant import Assistant
from arise_app.desktop import Controller
from arise_app.orb import build_orb


@unittest.skipUnless(shutil.which('node'), 'Node required for protocol fixture')
class DictationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.runtime = Assistant(self.temp.name)
        _, self.orb = build_orb(self.app, 96, 20, 20)
        self.controller = Controller(self.app, self.runtime, self.orb, start_voice=False)
        self.panel = self.controller.panel
        self.panel.show()
        self.runtime.steer = Mock()
        self.helper = Path(self.temp.name) / 'fake-dictation.cjs'
        self.helper.write_text("""
const rl=require('node:readline').createInterface({input:process.stdin});
const send=x=>console.log(JSON.stringify(x));
send({type:'state',state:'recording'});
rl.on('line',line=>{
  if(line==='stop') {send({type:'state',state:'transcribing'}); setTimeout(()=>{
    send({type:'result',text:'Hola ARISE',truncated:false});process.exit(0);
  },80);}
  if(line==='cancel') {send({type:'result',text:'LATE',truncated:false});process.exit(0);}
});
""", encoding='utf-8')
        original = self.controller.dictation.start
        self.controller.dictation.start = lambda config, chat, **kw: original(config, chat, script=self.helper)

    def wait_for(self, predicate):
        for _ in range(150):
            if predicate(): return
            QTest.qWait(20)
        self.fail('Timed out waiting for dictation state')

    def tearDown(self):
        self.controller.dictation.close()
        self.wait_for(lambda: not self.controller.workers)
        self.controller.close()
        self.orb.removeEventFilter(self.controller); self.orb.close(); self.panel.close()
        self.runtime.storage.db.close(); self.temp.cleanup()

    def record(self):
        QTest.mouseClick(self.panel.mic_button, Qt.LeftButton)
        self.wait_for(lambda: self.controller.dictation.state == 'recording')

    def test_two_clicks_insert_only_into_draft_and_preserve_edits(self):
        self.panel.input.setPlainText('Antes')
        self.record()
        self.assertIn('↑', self.panel.mic_button.toolTip())
        self.assertTrue(self.panel.mic_button.isChecked())
        self.panel.input.setPlainText('Escribí mientras grababa:')
        QTest.keyClick(self.panel.input, Qt.Key_Return)
        self.runtime.steer.assert_not_called()
        cursor = self.panel.input.textCursor(); cursor.movePosition(cursor.MoveOperation.End)
        self.panel.input.setTextCursor(cursor)
        QTest.mouseClick(self.panel.mic_button, Qt.LeftButton)
        self.wait_for(lambda: self.controller.dictation.state == 'idle')
        self.assertEqual(self.panel.input.toPlainText(), 'Escribí mientras grababa: Hola ARISE')
        self.runtime.steer.assert_not_called()
        self.assertFalse(self.controller.voice.muted)
        self.assertFalse(self.panel.mic_button.isChecked())
        self.panel.input.undo()
        self.assertEqual(self.panel.input.toPlainText(), 'Escribí mientras grababa:')

    def test_cancel_discards_late_result_and_allows_next_recording(self):
        self.panel.input.setPlainText('Borrador')
        self.record(); self.controller.cancel_dictation()
        self.wait_for(lambda: self.controller.dictation.state == 'idle')
        self.assertEqual(self.panel.input.toPlainText(), 'Borrador')
        self.runtime.steer.assert_not_called()
        self.record(); self.controller.cancel_dictation()
        self.wait_for(lambda: self.controller.dictation.state == 'idle')

    def test_chat_switch_discards_result(self):
        self.record()
        self.runtime.switch_conversation()
        self.controller.poll()
        self.wait_for(lambda: self.controller.dictation.state == 'idle')
        self.assertNotIn('LATE', self.panel.input.toPlainText())
        self.runtime.steer.assert_not_called()

    def test_install_does_not_start_recording_and_keeps_draft(self):
        self.helper.write_text("console.log(JSON.stringify({type:'state',state:'installing'}));console.log(JSON.stringify({type:'installed'}));", encoding='utf-8')
        self.panel.input.setPlainText('Sin cambios')
        QTest.mouseClick(self.panel.mic_button, Qt.LeftButton)
        self.wait_for(lambda: self.controller.dictation.state == 'idle')
        self.assertEqual(self.panel.input.toPlainText(), 'Sin cambios')
        self.assertIn('Dictado listo', self.panel.connection_notice.full_text)
        self.runtime.steer.assert_not_called()

    def test_failure_restores_existing_mute_and_draft(self):
        self.controller.voice.mute(True)
        self.helper.write_text("console.log(JSON.stringify({type:'error',code:'capture'}));", encoding='utf-8')
        self.panel.input.setPlainText('Conservar')
        QTest.mouseClick(self.panel.mic_button, Qt.LeftButton)
        self.wait_for(lambda: self.controller.dictation.state == 'idle')
        self.assertTrue(self.controller.voice.muted)
        self.assertEqual(self.panel.input.toPlainText(), 'Conservar')
        self.assertIn('permisos', self.panel.connection_notice.full_text)

    def test_cancel_during_preparation_never_opens_capture(self):
        self.controller.dictation.start = Mock()
        QTest.mouseClick(self.panel.mic_button, Qt.LeftButton)
        self.controller.cancel_dictation()
        self.wait_for(lambda: self.controller.dictation.state == 'idle')
        self.controller.dictation.start.assert_not_called()
        self.assertFalse(self.controller.voice.muted)

    def test_exit_terminates_capture_process(self):
        import psutil
        self.record()
        pid = self.controller.dictation.process.processId()
        self.controller.close()
        self.assertFalse(psutil.pid_exists(pid))
        self.assertFalse(self.controller.voice.muted)
