import os
import psutil
import sys
import tempfile
import time
import unittest
from pathlib import Path
from arise_app.processes import JsonProcess

class ProcessTreeTests(unittest.TestCase):
    def test_owned_grandchild_is_closed_with_json_process(self):
        with tempfile.TemporaryDirectory() as root:
            file=Path(root)/'child.pid'
            heartbeat=Path(root)/'heartbeat'
            child_code="import sys,time;from pathlib import Path\nfor i in range(1200):\n Path(sys.argv[1]).write_text(str(i));time.sleep(.05)"
            code="import subprocess,sys,time;from pathlib import Path;p=subprocess.Popen([sys.executable,'-c',sys.argv[2],sys.argv[3]]);Path(sys.argv[1]).write_text(str(p.pid));time.sleep(60)"
            process=JsonProcess([sys.executable,'-c',code,str(file),child_code,str(heartbeat)])
            child=None
            try:
                deadline=time.monotonic()+3
                while (not file.is_file() or not heartbeat.is_file()) and time.monotonic()<deadline:time.sleep(.02)
                child=psutil.Process(int(file.read_text())) if os.name=='nt' else None
                self.assertTrue(heartbeat.is_file())
                process.close()
                self.assertIsNotNone(process.process.poll())
                before=heartbeat.read_text();time.sleep(.2);self.assertEqual(heartbeat.read_text(),before)
                if child:
                    try:self.assertIn(child.status(),(psutil.STATUS_ZOMBIE,psutil.STATUS_DEAD))
                    except psutil.NoSuchProcess:pass
            finally:
                process.close()
                if child:
                    try:child.kill()
                    except psutil.NoSuchProcess:pass
