import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from arise_app.owned_engine import prepare, environment
from arise_app.bundle import configure_bundle


class OwnedEngineTests(unittest.TestCase):
    def fixture(self, root):
        bundle=root/'app/bundle';modules=bundle/'node/node_modules'
        gentle=modules/'gentle-pi';(gentle/'extensions').mkdir(parents=True)
        (gentle/'package.json').write_text(json.dumps({'name':'gentle-pi','version':'4.7.0','peerDependencies':{'@earendil-works/pi-coding-agent':'>=1.2.0'}}))
        pi=modules/'@earendil-works/pi-coding-agent';(pi/'dist/bundle').mkdir(parents=True)
        (pi/'package.json').write_text(json.dumps({'name':'@earendil-works/pi-coding-agent','version':'1.5.0','bin':{'pi':'dist/bundle/cli.js'}}))
        (pi/'dist/bundle/cli.js').write_text('// fixture')
        (bundle/'node/node.exe').write_text('fixture')
        memory=modules/'gentle-engram';memory.mkdir()
        (memory/'package.json').write_text(json.dumps({'name':'gentle-engram','engram':{'startupPolicy':1}}))
        (bundle/'engram').mkdir();(bundle/'engram/engram.exe').write_text('fixture')
        manifest={'owned_engine':1,'pi_command':['@bundle/node/node.exe','@bundle/node/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js'],
                  'gentle_path':'@bundle/node/node_modules/gentle-pi','engram_bin':'@bundle/engram/engram.exe',
                  'memory_package':'@bundle/node/node_modules/gentle-engram','versions':{'gentle':'4.7.0','pi':'1.5.0'}}
        (bundle/'manifest.json').write_text(json.dumps(manifest))
        config={'pi_command':['global-pi'],'gentle_path':'global-gentle','gentle_agent_home':'global-home','engram_bin':'global-engram','mcp':{}}
        runtime=SimpleNamespace(storage=SimpleNamespace(root=root/'data',config=config),emit=lambda *a:None)
        runtime.settings=lambda changes:config.update(changes)
        return runtime,bundle,manifest

    def test_bundle_overrides_global_selection_once_and_preserves_own_auth_on_upgrade(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);r,b,m=self.fixture(root)
            with patch('arise_app.bundle.application_root',return_value=b.parent):
                configure_bundle(r)
                home=Path(r.storage.config['gentle_agent_home'])
                (home/'auth.json').write_text('PRIVATE-AUTH')
                settings=json.loads((home/'settings.json').read_text());settings['model']='preferred';(home/'settings.json').write_text(json.dumps(settings))
                self.assertEqual(configure_bundle(r)['configured'],[])
                self.assertEqual((home/'auth.json').read_text(),'PRIVATE-AUTH')
                self.assertEqual(json.loads((home/'settings.json').read_text())['model'],'preferred')
                self.assertEqual(len(json.loads((home/'settings.json').read_text())['packages']),2)
            backup=json.loads((root/'data/engine/selection-backup.json').read_text())
            self.assertEqual(backup['pi_command'],['global-pi'])
            self.assertEqual(r.storage.config['pi_command'][0],str(b/'node/node.exe'))
            self.assertEqual(r.storage.config['engram_bin'],str(b/'engram/engram.exe'))

    def test_external_mode_is_not_adopted_and_incomplete_bundle_fails_before_config(self):
        with tempfile.TemporaryDirectory() as t:
            r,b,m=self.fixture(Path(t));r.storage.config['engine_mode']='external'
            self.assertEqual(prepare(r,b,m),{})
            r.storage.config['engine_mode']='bundled';before=dict(r.storage.config)
            (b/'node/node.exe').unlink()
            with self.assertRaises(RuntimeError):prepare(r,b,m)
            self.assertEqual(r.storage.config,before)
            self.assertFalse((r.storage.root/'engine').exists())

    def test_env_isolates_config_and_private_memory_and_keeps_identity(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);r,b,m=self.fixture(root);r.storage.config.update(prepare(r,b,m))
            real=root/'user';real.mkdir();(real/'.gitconfig').write_text('[user]')
            base={'HOME':str(real),'USERPROFILE':str(real),'GENTLE_PI_GENTLE_AI_DEV_BINARY':'foreign',
                  'GENTLE_PI_AGENTS_CHILD':'1','PI_CODING_AGENT_DIR':'foreign', 'NODE_OPTIONS':'--import foreign',
                  'ENGRAM_URL':'http://foreign','Path':'system-tools','ARISE_TERMINAL_TASK':'mailbox'}
            env=environment(base,r.storage.config)
            self.assertEqual(base['HOME'],str(real))
            self.assertEqual(env['HOME'],str(root/'data/engine/home'))
            self.assertEqual(env['GIT_CONFIG_GLOBAL'],str(real/'.gitconfig'))
            self.assertEqual(env['ENGRAM_DATA_DIR'],str(root/'data/engine/memory'))
            self.assertEqual(env['ENGRAM_SERVER_MODE'],'session-owned')
            for key in ('ENGRAM_URL','NODE_OPTIONS','GENTLE_PI_GENTLE_AI_DEV_BINARY','GENTLE_PI_AGENTS_CHILD'):
                self.assertNotIn(key,env)
            self.assertEqual(env['ARISE_TERMINAL_TASK'],'mailbox')
            self.assertEqual([k for k in env if k.upper()=='PATH'],['PATH'])

    def test_manifest_cannot_escape_bundle(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);r,b,m=self.fixture(root);m['gentle_path']='@bundle/../../foreign'
            with self.assertRaises(RuntimeError):prepare(r,b,m)

    def test_chat_preferences_cannot_restore_foreign_engine_paths(self):
        from arise_app.assistant import Assistant
        with tempfile.TemporaryDirectory() as t:
            r=Assistant(Path(t)/'data')
            try:
                path=Path(r.sessions.get(r.conversation)['folder'])/'preferences.json'
                path.write_text(json.dumps({'pi_command':['foreign'], 'gentle_path':'foreign', 'agent_model':'chosen', 'code_enabled':False}))
                r.storage.config.update(engine_mode='bundled',owned_engine_root=str(Path(t)/'engine'))
                restored=r.sessions.preferences(r.conversation)
                self.assertNotIn('pi_command',restored)
                self.assertNotIn('gentle_path',restored)
                self.assertEqual(restored['agent_model'],'chosen')
                self.assertFalse(restored['code_enabled'])
            finally:r.close()

    def test_real_47_rpc_uses_own_home_without_global_gentle(self):
        import shutil
        import threading
        from arise_app.assistant import Assistant
        from arise_app.server import make_server
        root_code=Path(__file__).resolve().parents[1]
        modules=root_code/'vendor/node_modules'
        gentle=modules/'gentle-pi'
        cli=modules/'@earendil-works/pi-coding-agent/dist/bundle/cli.js'
        self.assertTrue(cli.is_file(), 'Pinned Pi must be installed for this test')
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);r=Assistant(root/'data');base=root/'data/engine';home=base/'agent';home.mkdir(parents=True)
            (home/'settings.json').write_text(json.dumps({'packages':[str(modules/'gentle-engram'), {'source':str(gentle),'extensions':[]}]}))
            r.settings({'pi_command':[shutil.which('node'),str(cli)],'gentle_path':str(gentle),'gentle_agent_home':str(home),
                        'owned_engine_root':str(base),'engine_mode':'bundled'})
            server=make_server(r);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                with patch.dict(os.environ,{'GENTLE_PI_GENTLE_AI_DEV_BINARY':'INVALID-EXTERNAL', 'ENGRAM_STARTUP_POLICY':'deny', 'PI_OFFLINE':'1'}):
                    state=r.connect_pi()
                    self.assertTrue(state['sessionId'])
                    self.assertTrue(r.capabilities()['gentle_verified'])
                    self.assertNotIn('mem_search',r.capabilities()['pi_tools_observed'])  # Explicit deny policy is respected.
                    self.assertIn('subagent_run',r.capabilities()['pi_tools_observed'])
                    self.assertTrue((home/'sessions').exists() or Path(r.sessions.get(r.conversation)['folder'],'session').exists())
                    self.assertTrue((base/'gentle-ai').exists())
            finally:
                r.close();server.shutdown();server.server_close();thread.join(5)
