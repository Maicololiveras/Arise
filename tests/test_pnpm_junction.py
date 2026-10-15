"""Native Windows evidence for the exact storage predicate shipped to Gentle."""
import base64
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from scripts.prepare_gentle_installer import adapt_windows_storage

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'arise_app/resources/pnpm-storage-check.ps1'

class StorageAdapterTests(unittest.TestCase):
    def test_adapter_embeds_exact_predicate_and_rejects_changed_contract(self):
        import json
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'installer.mjs'
            path.write_text('before\nconst aclCheck = String.raw`old`;\nafter')
            adapt_windows_storage(path)
            self.assertEqual(path.read_text(), 'before\nconst aclCheck = '+json.dumps(SCRIPT.read_text())+';\nafter')
            with self.assertRaises(RuntimeError):adapt_windows_storage(path)

@unittest.skipUnless(os.name == 'nt', 'Requires native Windows junctions and ACLs')
class WindowsJunctionTests(unittest.TestCase):
    def setUp(self):
        from arise_app.gentle_setup import prepare_installer_stage
        self.root,self.env=prepare_installer_stage()
        self.env['LOCALAPPDATA']=str(self.root)
        self.target=self.root/'pnpm/store/v11/links/@/pnpm/11.1.1'/('a'*64)/'node_modules/pnpm'
        self.target.mkdir(parents=True)
        (self.target/'bin').mkdir();(self.target/'bin/pnpm.mjs').write_text('// fixture')
        self.link=self.root/'pnpm/global/v11/f68-fixture/node_modules/pnpm'
        self.link.parent.mkdir(parents=True)
        self.env.update(ARISE_TEST_LINK=str(self.link),ARISE_TEST_TARGET=str(self.target))
        self.ps("New-Item -ItemType Junction -Path $env:ARISE_TEST_LINK -Target $env:ARISE_TEST_TARGET | Out-Null")

    def tearDown(self):
        shutil.rmtree(self.root)

    def ps(self, script, check=True):
        encoded=base64.b64encode(script.encode('utf-16-le')).decode('ascii')
        return subprocess.run([str(Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'),
            '-NoLogo','-NoProfile','-NonInteractive','-EncodedCommand',encoded],
            env=self.env,capture_output=True,text=True,timeout=30,check=check)

    def evidence(self,path):
        self.env['GENTLE_WINDOWS_CHECK']=str(path)
        result=self.ps(SCRIPT.read_text(),check=False)
        return result.returncode,result.stdout.strip()

    def test_known_junction_and_plain_file_preserve_permissions(self):
        sddl="([IO.Directory]::GetAccessControl($env:ARISE_TEST_TARGET)).GetSecurityDescriptorSddlForm([Security.AccessControl.AccessControlSections]::All)"
        before=self.ps(sddl).stdout
        self.assertEqual(self.evidence(self.link/'bin/pnpm.mjs'),(0,'safe'))
        self.assertEqual(self.evidence(self.target/'bin/pnpm.mjs'),(0,'safe'))
        self.assertEqual(self.ps(sddl).stdout,before)

    def test_external_and_nested_junctions_are_rejected(self):
        external=self.root/'external';external.mkdir();(external/'bin').mkdir()
        (external/'bin/pnpm.mjs').write_text('// external')
        self.link.rmdir()
        self.env['ARISE_TEST_TARGET']=str(external)
        self.ps("New-Item -ItemType Junction -Path $env:ARISE_TEST_LINK -Target $env:ARISE_TEST_TARGET | Out-Null")
        self.assertEqual(self.evidence(self.link/'bin/pnpm.mjs'),(0,'unsafe:ancestor-reparse'))
        self.link.rmdir()
        shutil.rmtree(self.target)
        self.env['ARISE_TEST_LINK']=str(self.target)
        self.ps("New-Item -ItemType Junction -Path $env:ARISE_TEST_LINK -Target $env:ARISE_TEST_TARGET | Out-Null")
        self.env.update(ARISE_TEST_LINK=str(self.link),ARISE_TEST_TARGET=str(self.target))
        self.ps("New-Item -ItemType Junction -Path $env:ARISE_TEST_LINK -Target $env:ARISE_TEST_TARGET | Out-Null")
        self.assertEqual(self.evidence(self.link/'bin/pnpm.mjs'),(0,'unsafe:ancestor-reparse'))

    def test_destination_write_access_is_rejected(self):
        self.ps("$p=Join-Path $env:ARISE_TEST_TARGET 'bin/pnpm.mjs'; $a=[IO.File]::GetAccessControl($p); $sid=New-Object Security.Principal.SecurityIdentifier('S-1-1-0'); $r=New-Object Security.AccessControl.FileSystemAccessRule($sid,'Modify','Allow'); $a.AddAccessRule($r); [IO.File]::SetAccessControl($p,$a)")
        self.assertEqual(self.evidence(self.link/'bin/pnpm.mjs'),(0,'unsafe:target-acl-mask'))

    def test_missing_destination_is_never_safe(self):
        shutil.rmtree(self.target)
        self.assertNotEqual(self.evidence(self.link/'bin/pnpm.mjs'),(0,'safe'))
