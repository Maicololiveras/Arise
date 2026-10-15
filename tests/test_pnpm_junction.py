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
            contract = '\nconst storageChecks = /^(?:policy|(?:target|parent|ancestor)-(?:reparse|owner|acl-mask))$/;\nfunction windowsPowerShell(env, script, data, processAdapter) { return processAdapter("powershell.exe", ["-Command", script], {...env,...data}); }'
            contract += '\nconst result = {status:0}; if (result.error || result.status !== 0) throw new Error("Windows prerequisite process failed");'
            path.write_text('// before\nconst aclCheck = String.raw`old`;\n// after'+contract)
            adapt_windows_storage(path)
            self.assertIn('const aclCheck = '+json.dumps(SCRIPT.read_text())+';',path.read_text())
            self.assertIn('Buffer.from(script, "utf16le").toString("base64")',path.read_text())
            self.assertNotIn('"-Command", script',path.read_text())
            with path.open('a',encoding='utf-8') as out:
                out.write('\nconsole.log(JSON.stringify(windowsPowerShell({}, aclCheck, {}, (_command,args) => args)));')
            result=subprocess.run(['node',str(path)],capture_output=True,text=True,check=True)
            args=json.loads(result.stdout)
            self.assertEqual(args[0],'-EncodedCommand')
            self.assertEqual(base64.b64decode(args[1]).decode('utf-16-le'),SCRIPT.read_text())
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
        self.env['ARISE_TEST_SCRIPT']=script
        self.env['ARISE_TEST_POWERSHELL']=str(Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe')
        code = "const r=require('node:child_process').spawnSync(process.env.ARISE_TEST_POWERSHELL,['-NoLogo','-NoProfile','-NonInteractive','-EncodedCommand',Buffer.from(process.env.ARISE_TEST_SCRIPT,'utf16le').toString('base64')],{encoding:'utf8',env:process.env,timeout:15000,windowsHide:true});process.stdout.write(r.stdout||'');process.stderr.write(r.stderr||'');process.exit(r.status===null?99:r.status);"
        return subprocess.run(['node','-e',code], env=self.env,capture_output=True,text=True,timeout=30,check=check)

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
