import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from arise_app.command_picker import CommandPicker

class CommandPickerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.calls=[];self.dialog=CommandPicker(None,self.calls.append)
        self.dialog.resize(340,360);self.dialog.show()
        self.dialog.set_commands([{'name':f'gentle:cmd-{n:03}','source':'extension','description':'Configuración de memoria' if n==99 else 'Otra opción'} for n in range(100)])
        self.app.processEvents()
    def tearDown(self):self.dialog.close()
    def test_long_catalog_scrolls_and_search_matches_description_without_accents(self):
        self.assertGreater(self.dialog.results.verticalScrollBar().maximum(),0)
        self.assertLessEqual(self.dialog.height(),360)
        self.dialog.search.setText('configuracion memoria')
        self.assertEqual(self.dialog.results.count(),1)
        QTest.keyClick(self.dialog.search,Qt.Key_Return)
        self.assertEqual(self.calls,['/gentle:cmd-099'])
    def test_empty_search_and_escape_never_execute(self):
        self.dialog.search.setText('no-match')
        QTest.keyClick(self.dialog.search,Qt.Key_Return)
        self.assertEqual(self.calls,[])
        QTest.keyClick(self.dialog,Qt.Key_Escape)
        self.assertFalse(self.dialog.isVisible())
    def test_keyboard_selection_and_literal_catalog_text(self):
        self.dialog.results.setFocus();QTest.keyClick(self.dialog.results,Qt.Key_Down)
        QTest.keyClick(self.dialog.results,Qt.Key_Return)
        self.assertEqual(self.calls,['/gentle:cmd-001'])
