"""Windows autocrlf must not change the byte-verified registry backport."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from scripts import patch_gentle

ROOT = Path(__file__).resolve().parents[1]


class RegistryCheckoutTests(unittest.TestCase):
    def test_windows_style_checkout_preserves_hash_and_applies_exact_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def git(*args):
                return subprocess.run(['git', '-C', str(root), *args], check=True,
                                      capture_output=True, text=True)
            git('init')
            git('config', 'core.autocrlf', 'true')
            shutil.copyfile(ROOT / '.gitattributes', root / '.gitattributes')
            folder = root / 'vendor/gentle-patches'; folder.mkdir(parents=True)
            source = folder / 'skill-registry.ts'
            shutil.copyfile(patch_gentle.SOURCE, source)
            shutil.copyfile(patch_gentle.SOURCE.with_suffix('.sha256'), source.with_suffix('.sha256'))
            git('add', '.gitattributes', 'vendor')
            source.unlink()
            git('checkout-index', '--force', '--all')
            data = source.read_bytes()
            self.assertNotIn(b'\r\n', data)
            self.assertEqual(hashlib.sha256(data).hexdigest(), source.with_suffix('.sha256').read_text().strip())
            package = root / 'package'; (package / 'extensions').mkdir(parents=True)
            (package / 'package.json').write_text(json.dumps({'name': 'gentle-pi', 'version': '4.7.0'}))
            target = package / 'extensions/skill-registry.ts'; target.write_bytes(b'original')
            with patch.object(patch_gentle, 'SOURCE', source):
                patch_gentle.apply(package)
                self.assertEqual(target.read_bytes(), data)
                source.write_bytes(data + b'// unexpected change\n')
                with self.assertRaisesRegex(RuntimeError, 'integrity mismatch'):
                    patch_gentle.apply(package)
                self.assertEqual(target.read_bytes(), data)
