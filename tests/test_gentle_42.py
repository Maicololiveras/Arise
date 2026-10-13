import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch
from arise_app.gentle_compat import require_compatible_pi
from arise_app.windows_prerequisites import prepare_shell_prerequisites
from scripts.prepare_gentle_installer import adapt

class Gentle42Tests(unittest.TestCase):
    def test_floor_follows_package_metadata(self):
        package={'version':'4.2.0','peerDependencies':{'@earendil-works/pi-coding-agent':'>=1.2.0'}}
        for version in ('1.1.0','0.99.1',None,'1.2.0-beta'):
            with self.assertRaisesRegex(RuntimeError,'Pi 1.2.0'):require_compatible_pi(package,version)
        require_compatible_pi(package,'1.2.0')
        package['peerDependencies']['@earendil-works/pi-coding-agent']='>=1.3.0'
        with self.assertRaisesRegex(RuntimeError,'Pi 1.3.0'):require_compatible_pi(package,'1.2.0')

    def test_new_preflight_leaves_managers_and_go_to_upstream(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            with patch('arise_app.windows_prerequisites.find_git',return_value=(root/'git.exe',root/'bash.exe')),patch('arise_app.windows_prerequisites.install_native') as native,patch('arise_app.windows_prerequisites.prepare_manager_directory') as managers:
                env=prepare_shell_prerequisites(root,root/'data')
            native.assert_not_called();managers.assert_not_called()
            self.assertIn(str(root),env['PATH'])

    def test_both_installer_paths_remain_owned_by_upstream(self):
        with tempfile.TemporaryDirectory() as temp:
            entry=Path(temp)/'installer.mjs'
            source='#!/usr/bin/env node\nconst handlers={...wizardHandlers({ platform, arch, env, run, fs }),};\n'
            entry.write_text(source);adapt(entry)
            self.assertTrue(entry.read_text().startswith('#!/usr/bin/env node\n'))
            self.assertIn('withAriseReport(wizardHandlers(',entry.read_text())
            with self.assertRaisesRegex(RuntimeError,'contrato'):adapt(entry)
