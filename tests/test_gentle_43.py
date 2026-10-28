"""Exercise ARISE's wrapper with the real pinned Gentle 4.5 launcher."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from arise_app.gentle_compat import require_compatible_pi

ROOT=Path(__file__).resolve().parents[1]
GENTLE=ROOT/'vendor/node_modules/gentle-pi'

class Gentle43Tests(unittest.TestCase):
    def test_real_package_floor(self):
        package=json.loads((GENTLE/'package.json').read_text())
        self.assertEqual(package['version'],'4.5.0')
        require_compatible_pi(package,'1.2.0')
        with self.assertRaises(RuntimeError):require_compatible_pi(package,'1.1.0')

    def test_wrapper_preserves_isolated_linked_and_custom_homes(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            cli=root/'probe.mjs'
            cli.write_text("console.log(JSON.stringify({home:process.env.PI_CODING_AGENT_DIR,config:process.env.GENTLE_SHELL_CONFIG_HOME,interactive:process.env.GENTLE_SHELL_INTERACTIVE_HOST,args:process.argv.slice(2)}))")
            for kind,home in [('isolated',root/'.gentle-shell/agent'),('linked',root/'.pi/agent'),('custom',root/'custom')]:
                with self.subTest(kind=kind):
                    home.mkdir(parents=True,exist_ok=True)
                    (home/'settings.json').write_text(json.dumps({'packages':[str(GENTLE)]}))
                    env={k:v for k,v in os.environ.items() if not k.startswith(('GENTLE_','ARISE_','PI_'))}
                    env.update(HOME=str(root),USERPROFILE=str(root),ARISE_GENTLE_ROOT=str(GENTLE),ARISE_GENTLE_HOME=str(home),GENTLE_SHELL_INTERACTIVE_HOST='1')
                    p=subprocess.run(['node',str(ROOT/'arise_app/resources/gentle-shell.mjs'),str(cli),'--mode','rpc'],env=env,capture_output=True,text=True,timeout=15)
                    self.assertEqual(p.returncode,0,p.stderr)
                    result=json.loads(p.stdout)
                    self.assertEqual(Path(result['home']),home)
                    self.assertEqual(result['interactive'],'1')
                    self.assertEqual(result['args'],['--mode','rpc'])
                    if kind=='isolated':self.assertEqual(Path(result['config']),root/'.gentle-shell/gentle-ai')
                    else:self.assertNotIn('config',result)
