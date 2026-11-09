import json,os,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from arise_app.discovery import detect_gentle_installation, resolve_pi

@unittest.skipUnless(shutil.which('node'),'Node required')
class NpmRecoveryTests(unittest.TestCase):
    def test_npm_recovers_official_home_and_bundle_entry_without_running_shell(self):
        with tempfile.TemporaryDirectory() as t:
            base=Path(t);modules=base/'npm/node_modules';gentle=modules/'gentle-pi'
            (gentle/'runtime').mkdir(parents=True);(gentle/'extensions').mkdir();(gentle/'bin').mkdir()
            (gentle/'package.json').write_text(json.dumps({'name':'gentle-pi','version':'4.5.0','peerDependencies':{'@earendil-works/pi-coding-agent':'>=1.2.0'}}))
            home=base/'gentle-agent';home.mkdir();(home/'settings.json').write_text('{}')
            (gentle/'runtime/gentle-shell-launcher.mjs').write_text('export const launcherConfigPath=()=>"absent-fixture";export const parseLauncherConfig=JSON.parse;export const resolveHome=({env})=>({dir:env.FIXTURE_HOME});')
            (gentle/'runtime/gentle-ai-binary.mjs').write_text('export function resolveGentleAiBinary(){return "fixture";}')
            pi=modules/'@earendil-works/pi-coding-agent';(pi/'dist/bundle').mkdir(parents=True)
            cli=pi/'dist/bundle/cli.js';cli.write_text('throw Error("Must not execute Pi during discovery")')
            (pi/'package.json').write_text(json.dumps({'name':'@earendil-works/pi-coding-agent','version':'1.4.0','bin':{'pi':'dist/bundle/cli.js'}}))
            env={**os.environ,'APPDATA':str(base),'LOCALAPPDATA':str(base),'USERPROFILE':str(base),'FIXTURE_HOME':str(home)}
            with patch.dict(os.environ,env):
                result=detect_gentle_installation(env)
                self.assertEqual(result['gentle_agent_home'],str(home));self.assertEqual(result['pi_command'][1],str(cli.resolve()))
                self.assertEqual(result['gentle_bundle_root'],'')
                self.assertEqual(detect_gentle_installation(env,package=gentle),result)
                node=shutil.which('node')
                with patch('arise_app.discovery.shutil.which',side_effect=lambda name,**_:node if name=='node' else None):
                    self.assertEqual(resolve_pi()[1],str(cli.resolve()))
