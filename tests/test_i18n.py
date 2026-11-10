import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from PySide6.QtWidgets import QApplication,QWidget,QVBoxLayout,QPushButton,QLineEdit,QTabWidget,QComboBox
from arise_app.i18n import LiveTranslator,tr,set_language

class LanguageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def tearDown(self):set_language('es')
    def test_live_switch_updates_existing_and_new_widgets_without_changing_user_data(self):
        root=QWidget();layout=QVBoxLayout(root)
        button=QPushButton('Guardar');button.setAccessibleName('Guardar');layout.addWidget(button)
        draft=QLineEdit('Guardar');draft.setPlaceholderText('Tu respuesta');layout.addWidget(draft)
        tabs=QTabWidget();tabs.addTab(QWidget(),'Herramientas');layout.addWidget(tabs)
        combo=QComboBox();combo.addItem('Guardar','stable-id');layout.addWidget(combo)
        translator=LiveTranslator(self.app,'es')
        try:
            translator.set_language('en')
            self.assertEqual(button.text(),'Save');self.assertEqual(button.accessibleName(),'Save')
            self.assertEqual(draft.text(),'Guardar');self.assertEqual(draft.placeholderText(),'Your answer')
            self.assertEqual(combo.currentText(),'Guardar');self.assertEqual(combo.currentData(),'stable-id')
            self.assertEqual(tabs.tabText(0),'Tools')
            late=QPushButton('Cancelar');layout.addWidget(late);translator.refresh()
            self.assertEqual(late.text(),'Cancel')
            button.setText('Cerrar');translator.refresh();self.assertEqual(button.text(),'Close')
            translator.set_language('es');self.assertEqual(button.text(),'Cerrar');self.assertEqual(tabs.tabText(0),'Herramientas')
        finally:translator.close();root.close()
    def test_paths_tokens_and_unknown_diagnostics_are_preserved(self):
        for value in ['C:\\Users\\Guardar','gpt-6.1-sol','fixture-secret','Unknown provider response']:
            self.assertEqual(tr(value,'en'),value)
        with self.assertRaises(ValueError):set_language('fr')
    def test_translated_agent_choices_return_original_protocol_value(self):
        from arise_app.task_dialog import TaskDialog
        dialog=TaskDialog({'method':'select','title':'Elegir perfil','options':['Crear perfil','Cerrar']})
        translator=LiveTranslator(self.app,'en')
        try:
            translator.refresh()
            self.assertEqual(dialog.input.currentText(),'Create profile')
            self.assertEqual(dialog.value(),'Crear perfil')
            translator.set_language('es')
            self.assertEqual(dialog.input.currentText(),'Crear perfil')
        finally:translator.close();dialog.close()
