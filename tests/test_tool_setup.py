import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from arise_app.tool_setup import _install
from arise_app.credentials import Credentials

class ToolSetupTests(unittest.TestCase):
    def test_private_components_configure_owned_runtime_and_real_catalog_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);bundle=root/'app/bundle';(bundle/'python').mkdir(parents=True)
            (bundle/'python/python.exe').write_bytes(b'fixture-executable');(bundle/'mcp_entry.py').write_text('# fixture launcher')
            config={'mcp':{}};events=[]
            runtime=SimpleNamespace(storage=SimpleNamespace(root=root,config=config),credentials=SimpleNamespace(get=lambda provider:'fixture-private-token'),mcp={},emit=lambda kind,data:events.append((kind,data)))
            runtime.settings=lambda changes:config.update(changes)
            runtime.connect_mcp=lambda name:SimpleNamespace(tools=[{'name':name+'-fixture-tool'}])
            archives={}
            for repo in ('screenview-mcp','inputcontrol-mcp'):
                data=io.BytesIO()
                with zipfile.ZipFile(data,'w') as archive:archive.writestr('owner-project-fixture/pyproject.toml','[project]\nname="fixture"\nversion="0.0.1"')
                archives[repo]=data.getvalue()
            def opener(url,timeout):
                for repo in archives:
                    if '/'+repo+'/zipball/' in url:return io.BytesIO(archives[repo])
                raise AssertionError(url)
            def metadata(url,opener):return {'sha':'a'*40} if '/commits/' in url else {'default_branch':'master'}
            with patch('arise_app.tool_setup.checked_run') as checked,patch('arise_app.tool_setup.application_root',return_value=root/'app'),patch('arise_app.tool_setup.github_opener',return_value=opener),patch('arise_app.tool_setup.github_json',side_effect=metadata),patch('arise_app.tool_setup.subprocess.run',return_value=SimpleNamespace(returncode=0)) as run:
                result=_install(runtime)
            self.assertEqual(checked.call_count,2)
            self.assertIn('--no-build-isolation',checked.call_args.args[0])
            self.assertEqual(result['catalogs'],{'screenview':1,'inputcontrol':1})
            self.assertTrue((root/'tools/installed.json').is_file())
            for spec in config['mcp'].values():self.assertEqual(spec['command'][0],str(root/'tools/python/python.exe'));self.assertTrue(spec['enabled'])
            for call in run.call_args_list:self.assertNotIn('fixture-private-token',str(call))
            self.assertTrue(any(kind=='tools_configured' for kind,_ in events))
    def test_github_credential_is_not_injected_into_pi_environment(self):
        with tempfile.TemporaryDirectory() as root:
            credentials=Credentials(root);credentials.save('github-updates','fixture-private-token',False)
            self.assertEqual(credentials.get('github-updates'),'fixture-private-token')
            self.assertNotIn('fixture-private-token',credentials.environment().values())
