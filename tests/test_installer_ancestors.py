"""Exercise the actual PowerShell ancestor routine against cyclic/reused PIDs."""
import os
from pathlib import Path
import subprocess
import unittest

@unittest.skipUnless(os.name == 'nt', 'Windows PowerShell required')
class InstallerAncestorTests(unittest.TestCase):
    def test_cycle_and_reused_parent_are_bounded(self):
        source=(Path(__file__).resolve().parents[1]/'arise_app/resources/stop-arise.ps1').read_text()
        function=source[source.index('function Protect-Ancestors'):source.index('Protect-Ancestors $all')]
        fixture='''
function Is-Arise($record) { return $false }
$records = @(
 [pscustomobject]@{ProcessId=10;ParentProcessId=20;CreationDate=1},
 [pscustomobject]@{ProcessId=20;ParentProcessId=10;CreationDate=1}
)
$protected=@{}
Protect-Ancestors $records 10 $protected
if($protected.Count -ne 2) { throw 'Cycle traversal incorrect' }
$records[1].CreationDate=2
$protected=@{}
Protect-Ancestors $records 10 $protected
if($protected.Count -ne 1) { throw 'Reused parent PID traversed' }
'''
        result=subprocess.run(['powershell.exe','-NonInteractive','-NoProfile','-Command',function+fixture],capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
