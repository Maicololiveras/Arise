"""Run all tests, preserve a machine-readable report, fail on failures or skipped Pi test."""
import json
import os
import platform
import sys
import time
import unittest
from pathlib import Path
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
class Result(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.records=[]
    def addSuccess(self,test):super().addSuccess(test);self.records.append({"test":test.id(),"status":"passed"})
    def addFailure(self,test,err):super().addFailure(test,err);self.records.append({"test":test.id(),"status":"failed"})
    def addError(self,test,err):super().addError(test,err);self.records.append({"test":test.id(),"status":"error"})
    def addSkip(self,test,reason):super().addSkip(test,reason);self.records.append({"test":test.id(),"status":"skipped","reason":reason})
start=time.time();suite=unittest.defaultTestLoader.discover(str(root/'tests'))
result=unittest.TextTestRunner(verbosity=2,resultclass=Result).run(suite)
output=Path(os.environ.get('ARISE_TEST_REPORT',str(root/'artifacts/test-results.json')));output.parent.mkdir(parents=True,exist_ok=True)
output.write_text(json.dumps({"platform":platform.platform(),"python":platform.python_version(),"duration_seconds":round(time.time()-start,3),"tests":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),"skipped":len(result.skipped),"records":result.records,"cloud_accounts_used":False},indent=2),encoding='utf-8')
raise SystemExit(0 if result.wasSuccessful() and not result.skipped else 1)
