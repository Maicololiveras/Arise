import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import time
import unittest
from types import SimpleNamespace
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication,QLineEdit
from arise_app.accounts_widget import AccountsDialog

class AccountsUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def wait(self,predicate):
        deadline=time.monotonic()+4
        while time.monotonic()<deadline:
            self.app.processEvents()
            if predicate():return
            time.sleep(.01)
        self.fail('UI did not settle')

    def test_masked_entry_model_selection_and_close_cancels_without_terminal(self):
        calls=[];state={'state':'idle'}
        def call(action,data):
            calls.append((action,dict(data)))
            if action=='providers':return {'providers':[{'id':'openai','name':'OpenAI','methods':['api_key'],'configured':True}]}
            if action=='models':return {'models':[{'id':'fixture-model','name':'Fixture model','provider':'openai'}]}
            if action=='start':state.update(state='prompt',prompt={'id':'prompt-1','kind':'secret','message':'API key'});return dict(state)
            if action=='status':return dict(state)
            if action=='answer':state.clear();state.update(state='done',provider='openai');return dict(state)
            return {'selected':True}
        runtime=SimpleNamespace(storage=SimpleNamespace(config={}),accounts=SimpleNamespace(call=call))
        dialog=AccountsDialog(runtime);dialog.show();dialog.resize(320,360)
        try:
            self.wait(lambda:dialog.connect.isEnabled())
            dialog.connect.click();self.wait(lambda:dialog.answer.isVisible())
            self.assertEqual(dialog.answer.echoMode(),QLineEdit.Password)
            dialog.answer.setText('fixture-secret');dialog.submit.click()
            self.wait(lambda:any(a=='answer' for a,d in calls))
            self.wait(lambda:dialog.select.isEnabled())
            dialog.select.click();self.wait(lambda:any(a=='select_model' for a,d in calls))
            self.assertEqual(dialog.answer.text(),'')
            self.assertTrue(dialog.cancel.isVisible())
            self.assertLess(dialog.cancel.geometry().bottom(),dialog.height())
            dialog.reject();self.wait(lambda:any(a=='close' for a,d in calls))
            self.assertFalse(dialog.timer.isActive())
        finally:dialog.reject();self.app.processEvents()
