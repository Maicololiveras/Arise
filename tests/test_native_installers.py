"""Publication must fail closed unless all six install gates and hashes pass."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('publish_native', ROOT / 'scripts/publish_native.py')
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


class NativePublicationTests(unittest.TestCase):
    def fixture(self, root):
        for system, extension in [('windows', '-Setup.exe'), ('linux', '.deb'), ('macos', '.pkg')]:
            for arch in ('x64', 'arm64'):
                target = f'{system}-{arch}'
                artifact = root / f'ARISE-{publisher.__version__}-{target}{extension}'
                artifact.write_bytes(b'installer-fixture')
                Path(str(artifact) + '.sha256').write_text(hashlib.sha256(artifact.read_bytes()).hexdigest() + '  ' + artifact.name)
                report = dict(target=target, profile_preserved=True)
                report.update({gate: 'passed' for gate in ['install', 'installed_engine_and_ui', 'same_version_reinstall', 'uninstall']})
                (root / f'{target}-installer.json').write_text(json.dumps(report))
                (root / f'{target}-smoke.json').write_text('{}')

    def test_corruption_blocks_release(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(publisher.subprocess, 'run') as run:
            root = Path(tmp); self.fixture(root)
            next(root.glob('*.deb')).write_bytes(b'corrupt')
            with self.assertRaisesRegex(RuntimeError, 'Checksum mismatch'):
                publisher.main(root)
            run.assert_not_called()

    def test_failed_preservation_blocks_release(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(publisher.subprocess, 'run') as run:
            root = Path(tmp); self.fixture(root)
            report = root / 'macos-arm64-installer.json'
            data = json.loads(report.read_text()); data['profile_preserved'] = False
            report.write_text(json.dumps(data))
            with self.assertRaisesRegex(RuntimeError, 'preservation'):
                publisher.main(root)
            run.assert_not_called()

    def test_verified_release_is_drafted_before_publication(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(publisher.subprocess, 'run') as run, patch.dict('os.environ', GITHUB_SHA='fixture-commit'):
            root = Path(tmp); self.fixture(root)
            publisher.main(root)
            self.assertEqual(run.call_count, 2)
            create, publish = [call.args[0] for call in run.call_args_list]
            self.assertIn('--draft', create)
            self.assertIn('--draft=false', publish)
            self.assertIn('--latest=false', publish)
            self.assertNotIn('--clobber', create)
