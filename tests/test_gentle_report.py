"""Exercise the report boundary, including the new private distribution path."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

class GentleReportTests(unittest.TestCase):
    def test_bundled_result_uses_its_node_pi_and_home(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);scripts=root/'scripts';scripts.mkdir();(root/'bin').mkdir()
            shutil.copy2(Path(__file__).resolve().parents[1]/'arise_app/resources/arise-result.mjs',root/'bin/arise-result.mjs')
            (scripts/'installer-probes.mjs').write_text('export function createProbes(){return {locateShell(){throw Error("global Shell must not be used")},locatePi(){throw Error("global Pi must not be used")}}}')
            (scripts/'bundled-install.mjs').write_text('import {join} from "node:path";export function prefixLayout({root}){return {versions:join(root,"versions"),node:join(root,"node.exe")}};export function activeVersion(){return "4.2.0-pi-1.2.0"}')
            prefix=root/'private';shell=prefix/'versions/4.2.0-pi-1.2.0/node_modules/gentle-pi'
            (shell/'runtime').mkdir(parents=True);(shell/'package.json').write_text('{"version":"4.2.0"}')
            (shell/'runtime/gentle-shell-launcher.mjs').write_text('export const launcherConfigPath=()=>"missing-fixture";export const parseLauncherConfig=JSON.parse;export const resolveHome=({env})=>({dir:env.TEST_HOME})')
            test='''import {withAriseReport} from './bin/arise-result.mjs';
import {readFile} from 'node:fs/promises';
const [root,home]=process.argv.slice(2);
const handlers=withAriseReport({collectPlan:async channel=>({channel}),runInstall:async()=>({outcome:'ready'})},{platform:process.platform,env:{TEST_HOME:home},run(){},fs:{}});
await handlers.collectPlan('release');
await handlers.runInstall({plan:{bundled:{root}}},()=>{});
console.log(await readFile('./arise-result.json','utf8'));
'''
            (root/'test.mjs').write_text(test)
            result=subprocess.run(['node',str(root/'test.mjs'),str(prefix),str(root/'agent')],cwd=root,capture_output=True,text=True,check=True)
            report=json.loads(result.stdout)
            self.assertEqual(report['status'],'ready')
            self.assertEqual(report['node'],str(prefix/'node.exe'))
            self.assertEqual(report['bundle_root'],str(prefix))
            self.assertEqual(report['agent_home'],str(root/'agent'))
            self.assertEqual(report['gentle_root'],str(shell))
