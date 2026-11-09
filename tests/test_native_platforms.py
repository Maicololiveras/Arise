import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from arise_app.platforms import target, data_directory, bundled_executable
from arise_app import updates


class NativePlatformTests(unittest.TestCase):
    def test_target_aliases_and_unknown_architecture(self):
        for system, machine, expected in [('Windows','AMD64','windows-x64'),('Windows','ARM64','windows-arm64'),('Linux','x86_64','linux-x64'),('Linux','aarch64','linux-arm64'),('Darwin','arm64','macos-arm64'),('Darwin','x86_64','macos-x64')]:
            self.assertEqual(target(system,machine),expected)
        with self.assertRaises(RuntimeError): target('Linux','i686')

    def test_linux_data_root_obeys_xdg(self):
        with patch('sys.platform','linux'), patch.dict(os.environ,{'XDG_DATA_HOME':'/private/data'}):
            self.assertEqual(data_directory(),Path('/private/data/ARISE-Orb'))

    def test_native_executable_preserves_explicit_bundle_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            expected=root/('node.exe' if os.name=='nt' else 'node')
            expected.touch()
            self.assertEqual(bundled_executable(root,'node'),expected)

    def test_preview_does_not_contact_windows_update_feed(self):
        with patch.object(Path,'is_file',return_value=True), patch.object(Path,'read_text',return_value=json.dumps({'channel':'qa','target':'linux-arm64','format':'native-preview'})):
            def forbidden(*args,**kwargs):self.fail('Preview contacted Windows feed')
            self.assertIsNone(updates.check_update(opener=forbidden))

    def test_foreign_engine_rejected_before_reading_packages(self):
        from arise_app.owned_engine import prepare
        from types import SimpleNamespace
        runtime=SimpleNamespace(storage=SimpleNamespace(config={}))
        with patch('arise_app.platforms.target',return_value='linux-arm64'):
            with self.assertRaisesRegex(RuntimeError,'another operating system'):
                prepare(runtime,Path('/missing'),{'owned_engine':1,'target':'windows-x64'})
