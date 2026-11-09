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

    def test_shutdown_exit_race_and_live_failure(self):
        source=(Path(__file__).resolve().parents[1]/'arise_app/resources/stop-arise.ps1').read_text()
        function=source[source.index('function Stop-OwnedProcess'):source.index("Trace ('Forced cleanup candidates:")]
        fixture=r'''
$ErrorActionPreference='Stop'
function Trace($message) {}
$record=[pscustomobject]@{ProcessId=123;CreationDate=10}
$script:calls=0
$script:stops=0
$script:mode='exit'
function Get-CimInstance {
    param($ClassName,$OperationTimeoutSec,$Filter)
    $script:calls++
    if ($script:mode -eq 'reuse') { return [pscustomobject]@{ProcessId=123;CreationDate=20} }
    if ($script:calls -eq 1 -or $script:mode -eq 'denied') { return $record }
}
function Stop-Process {
    param($Id,[switch]$Force,$ErrorAction)
    $script:stops++
    throw 'Simulated stop failure'
}
Stop-OwnedProcess $record @{}
if ($script:calls -ne 2 -or $script:stops -ne 1) { throw 'Exit race not checked' }
$script:calls=0; $script:mode='denied'; $caught=$false
try { Stop-OwnedProcess $record @{} } catch { $caught=$true }
if (-not $caught) { throw 'Live process failure was ignored' }
$script:stops=0; $script:mode='reuse'
Stop-OwnedProcess $record @{}
if ($script:stops -ne 0) { throw 'Reused PID was stopped' }
$script:calls=0
Stop-OwnedProcess $record @{123=$true}
if ($script:calls -ne 0) { throw 'Protected process queried' }
'''
        result=subprocess.run(['powershell.exe','-NonInteractive','-NoProfile','-Command',function+fixture],capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
