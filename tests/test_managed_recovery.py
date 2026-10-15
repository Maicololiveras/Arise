"""Execute the discovery probe, with no global pnpm and no running agent."""
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from arise_app.discovery import detect_gentle_installation

class ManagedRecoveryTests(unittest.TestCase):
    def test_private_runtime_home_and_failure_are_not_replaced_by_globals(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp); prefix=base/'local/gentle-shell'; prefix.mkdir(parents=True)
            (prefix/'.gentle-shell-bundle').write_text('gentle-shell bundled install\n')
            version=prefix/'versions/v4.2.0'; modules=version/'node_modules'
            shell=modules/'gentle-pi'; (shell/'runtime').mkdir(parents=True); (shell/'extensions').mkdir()
            # Gentle writes exact LF bytes with Node, including on Windows.
            (version/'.gentle-shell-version').write_bytes(b'v4.2.0\n')
            (shell/'package.json').write_text(json.dumps({'name':'gentle-pi','version':'4.2.0'}))
            home=base/'official-agent';home.mkdir();(home/'settings.json').write_text('{}')
            (shell/'runtime/gentle-shell-launcher.mjs').write_text('export const launcherConfigPath=()=>"missing-fixture";export const parseLauncherConfig=JSON.parse;export const resolveHome=({env})=>({dir:env.FIXTURE_HOME});')
            (shell/'runtime/gentle-ai-binary.mjs').write_text('export function resolveGentleAiBinary(){if(process.env.FIXTURE_REJECT) throw Error("integrity rejected");}')
            pi=modules/'@earendil-works/pi-coding-agent';(pi/'dist').mkdir(parents=True)
            (pi/'dist/cli.js').write_text('throw Error("must not start Pi during discovery")')
            (pi/'package.json').write_text(json.dumps({'name':'@earendil-works/pi-coding-agent','version':'1.2.0','bin':{'pi':'dist/cli.js'}}))
            (prefix/'node.exe').write_text('fixture runtime, never executed by probe')
            bundle=base/'app/bundle';(bundle/'node').mkdir(parents=True)
            shutil.copy2(shutil.which('node'),bundle/'node/node.exe')
            helper=bundle/'gentle-installer/scripts/bundled-install.mjs';helper.parent.mkdir(parents=True)
            helper.write_text('import {join} from "node:path";export const prefixLayout=({root})=>({versions:join(root,"versions"),node:join(root,"node.exe")});export const activeVersion=()=>"v4.2.0";export const setupEnvironment=(_, {env})=>env;')
            env={**os.environ,'LOCALAPPDATA':str(base/'local'),'USERPROFILE':str(base),'FIXTURE_HOME':str(home)}
            with patch('arise_app.bundle.application_root',return_value=base/'app'),patch('arise_app.discovery.shutil.which',return_value=None):
                found=detect_gentle_installation(env)
                self.assertEqual(found['gentle_bundle_root'],str(prefix))
                self.assertEqual(found['gentle_agent_home'],str(home))
                self.assertEqual(found['pi_command'],[str(prefix/'node.exe'),str(pi/'dist/cli.js')])
                # Reproduce the former Windows fixture defect on every platform.
                (version/'.gentle-shell-version').write_bytes(b'v4.2.0\r\n')
                with self.assertRaisesRegex(RuntimeError,'incompleto'):
                    detect_gentle_installation(env)
                (version/'.gentle-shell-version').write_bytes(b'v4.2.0\n')
                with self.assertRaisesRegex(RuntimeError,'incompleto'):
                    detect_gentle_installation({**env,'FIXTURE_REJECT':'1'})
                (version/'.gentle-shell-version').write_bytes(b'installing v4.2.0 123\n')
                with self.assertRaisesRegex(RuntimeError,'incompleto'):
                    detect_gentle_installation(env)

    def test_ambiguous_prefixes_require_explicit_selection(self):
        with patch('arise_app.discovery.managed_gentle_candidates',return_value=[Path('/one'),Path('/two')]),patch('arise_app.discovery.linked_gentle_candidate',return_value=None):
            with self.assertRaisesRegex(RuntimeError,'varios'):
                detect_gentle_installation({})
