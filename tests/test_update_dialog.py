import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog
from arise_app.update_dialog import UpdateDialog
from arise_app.desktop import STYLE


class UpdateDialogTests(unittest.TestCase):
    def test_long_notes_scroll_without_hiding_actions_and_escape_cancels(self):
        app = QApplication.instance() or QApplication([])
        app.setStyleSheet(STYLE)
        dialog = UpdateDialog({'version':'0.4.18', 'notes':('Novedades de ARISE: mejora de instalación y recuperación.\n' * 160)}, '0.4.17')
        try:
            dialog.resize(340, 440)
            dialog.show(); app.processEvents()
            self.assertLessEqual(dialog.height(), 440)
            bar = dialog.notes.verticalScrollBar()
            self.assertGreater(bar.maximum(), 0)
            for button in (dialog.install, dialog.dismiss):
                self.assertTrue(dialog.rect().contains(button.geometry()))
            dialog.notes.setFocus()
            QTest.keyClick(dialog.notes, Qt.Key_PageDown)
            app.processEvents()
            self.assertGreater(bar.value(), 0)
            self.assertFalse(dialog.notes.horizontalScrollBar().isVisible())
            QTest.keyClick(dialog, Qt.Key_Escape)
            self.assertEqual(dialog.result(), QDialog.Rejected)
        finally: dialog.close()

    def test_install_is_explicit_and_close_never_accepts(self):
        app = QApplication.instance() or QApplication([])
        for install in (False, True):
            dialog = UpdateDialog({'version':'0.4.18','notes':'Cambio breve'}, '0.4.17')
            dialog.show(); app.processEvents()
            accepted=[]; dialog.accepted.connect(lambda:accepted.append(True))
            QTest.mouseClick(dialog.install if install else dialog.dismiss, Qt.LeftButton)
            self.assertEqual(bool(accepted), install)
            dialog.close()
