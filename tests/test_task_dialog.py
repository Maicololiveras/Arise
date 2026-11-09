import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog
from arise_app.task_dialog import TaskDialog
from arise_app.desktop import STYLE

class TaskDialogTests(unittest.TestCase):
    def test_long_questions_keep_actions_visible_and_escape_rejects(self):
        app = QApplication.instance() or QApplication([])
        app.setStyleSheet(STYLE)
        for method in ('confirm', 'select', 'input', 'editor'):
            with self.subTest(method=method):
                d = TaskDialog(dict(method=method, message='Long question\n'*300,
                                    options=['Local execution in this chat','Reject'], prefill='draft'))
                d.resize(340, 360); d.show(); app.processEvents()
                self.assertLessEqual(d.height(), 360)
                self.assertGreater(d.details.verticalScrollBar().maximum(), 0)
                for button in (d.accept_button,d.reject_button):
                    self.assertTrue(d.rect().contains(button.mapTo(d,QPoint(0,0))))
                    self.assertTrue(d.rect().contains(button.mapTo(d,button.rect().bottomRight())))
                QTest.keyClick(d,Qt.Key_Escape)
                self.assertEqual(d.result(),QDialog.Rejected)
                if method=='confirm': self.assertEqual(d.value(),'No')
                d.close()

    def test_confirm_requires_explicit_accept(self):
        app = QApplication.instance() or QApplication([])
        d=TaskDialog(dict(method='confirm',message='Allow?'))
        d.show();app.processEvents()
        QTest.mouseClick(d.accept_button,Qt.LeftButton)
        self.assertEqual(d.result(),QDialog.Accepted);self.assertEqual(d.value(),'Sí')
        d.close()
