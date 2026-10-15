import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from arise_app.tool_setup import _install_private_into,install_forge
from arise_app.credentials import Credentials

class ToolSetupTests(unittest.TestCase):
    def test_forge_uses_shipped_npm_and_cleans_failed_install(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);bundle=root/'bundle';tools=root/'tools';tools.mkdir()
            node=bundle/'node/node.exe';node.parent.mkdir(parents=True);node.write_bytes(b'fixture')
            npm=bundle/'node/node_modules/npm/bin/npm-cli.js';npm.parent.mkdir(parents=True);npm.write_text('// fixture')
            payload=io.BytesIO()
            with zipfile.ZipFile(payload,'w') as archive:
                archive.writestr('forge/package.json','{}')
                archive.writestr('forge/package-lock.json','{}')
            def metadata(url,opener):return {'sha':'a'*40} if '/commits/' in url else {'default_branch':'main'}
            def build(command,label,**kwargs):
                self.assertEqual(command[:2],[str(node),str(npm)])
                if command[2:]==['run','build']:
                    entry=Path(kwargs['cwd'])/'dist/bin/forge-mcp-cli.js';entry.parent.mkdir(parents=True);entry.write_text('// fixture')
            with patch('arise_app.tool_setup.github_json',side_effect=metadata),patch('arise_app.tool_setup.checked_run',side_effect=build):
                spec,record=install_forge(bundle,tools,lambda *a,**k:io.BytesIO(payload.getvalue()))
            self.assertTrue(Path(spec['command'][1]).is_file())
            before=set(tools.iterdir())
            with patch('arise_app.tool_setup.github_json',side_effect=metadata),patch('arise_app.tool_setup.checked_run',side_effect=RuntimeError('build failed')):
                with self.assertRaisesRegex(RuntimeError,'build failed'):
                    install_forge(bundle,tools,lambda *a,**k:io.BytesIO(payload.getvalue()))
            self.assertEqual(set(tools.iterdir()),before)

    def test_private_components_configure_owned_runtime_and_real_catalog_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);bundle=root/'app/bundle';(bundle/'python').mkdir(parents=True)
            (bundle/'python/python.exe').write_bytes(b'fixture-executable');(bundle/'mcp_entry.py').write_text('# fixture launcher')
            config={'mcp':{}};events=[]
            runtime=SimpleNamespace(storage=SimpleNamespace(root=root,config=config),credentials=SimpleNamespace(get=lambda provider:'fixture-private-token'),mcp={},emit=lambda kind,data:events.append((kind,data)))
            runtime.settings=lambda changes:config.update(changes)
            runtime.connect_mcp=lambda name:SimpleNamespace(tools=[{'name':name+'-fixture-tool'}])
            archives={}
            for repo in ('screenview-mcp','inputcontrol-mcp','transcripcion-ia'):
                data=io.BytesIO()
                with zipfile.ZipFile(data,'w') as archive:archive.writestr('owner-project-fixture/pyproject.toml','[project]\nname="fixture"\nversion="0.0.1"')
                archives[repo]=data.getvalue()
            def opener(url,timeout):
                for repo in archives:
                    if '/'+repo+'/zipball/' in url:return io.BytesIO(archives[repo])
                raise AssertionError(url)
            def metadata(url,opener):return {'sha':'a'*40} if '/commits/' in url else {'default_branch':'master'}
            with patch('arise_app.tool_setup.install_forge',return_value=({'command':['fixture-forge'],'enabled':True},{'repo':'forge-mcp','commit':'b'*40})),patch('arise_app.tool_setup.checked_run') as checked,patch('arise_app.tool_setup.application_root',return_value=root/'app'),patch('arise_app.tool_setup.github_opener',return_value=opener),patch('arise_app.tool_setup.github_json',side_effect=metadata),patch('arise_app.tool_setup.subprocess.run',return_value=SimpleNamespace(returncode=0)) as run:
                tools=root/'tools';tools.mkdir();result=_install_private_into(runtime,tools)
            self.assertEqual(checked.call_count,3)
            self.assertIn('--no-build-isolation',checked.call_args_list[1].args[0])
            self.assertEqual(result['catalogs'],{'screenview':1,'inputcontrol':1,'transcripcion':1,'forge':1})
            self.assertTrue((root/'tools/installed.json').is_file())
            for spec in [config['mcp'][name] for name in ('screenview','inputcontrol','transcripcion')]:self.assertTrue(Path(spec['command'][0]).is_file());self.assertTrue(Path(spec['command'][0]).is_relative_to(root/'tools'));self.assertTrue(spec['enabled'])
            for call in run.call_args_list:self.assertNotIn('fixture-private-token',str(call))
            self.assertTrue(any(kind=='tools_configured' for kind,_ in events))
    def test_github_credential_is_not_injected_into_pi_environment(self):
        with tempfile.TemporaryDirectory() as root:
            credentials=Credentials(root);credentials.save('github-updates','fixture-private-token',False)
            self.assertEqual(credentials.get('github-updates'),'fixture-private-token')
            self.assertNotIn('fixture-private-token',credentials.environment().values())

    def test_optional_failure_does_not_discard_public_tools(self):
        import threading
        from arise_app.tool_setup import auto_setup
        events=[]; installed=[]
        runtime=SimpleNamespace(storage=SimpleNamespace(config={'mcp':{}}),
            credentials=None, transition_lock=threading.RLock(), busy=False,
            emit=lambda kind,data:events.append(data['text']))
        def install(runtime, selected):
            name=selected[0]
            if name=='transcripcion':raise RuntimeError('fixture import failure')
            installed.append(name)
        with patch('arise_app.tool_setup.os.name','nt'), \
             patch('arise_app.tool_setup.github_token',return_value='fixture'), \
             patch('arise_app.tool_setup.command_available',return_value=False), \
             patch('arise_app.tool_setup.setup_desktop_tools',side_effect=install):
            auto_setup(runtime)
        self.assertEqual(installed,['screenview','inputcontrol','forge'])
        self.assertTrue(any('transcripcion: fixture import failure' in e for e in events))
