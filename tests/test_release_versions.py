"""Catch installer/runtime drift before the expensive Windows packaging smoke."""
from pathlib import Path
import re
import tomllib
import unittest
from unittest.mock import patch
from arise_app import __version__

ROOT = Path(__file__).resolve().parents[1]

class ReleaseVersionTests(unittest.TestCase):
    def test_shipped_versions_agree(self):
        sources = {
            'Python package': tomllib.loads((ROOT/'pyproject.toml').read_text(encoding='utf-8'))['project']['version'],
            'Inno installer': re.search(r'^#define AppVersion "([^"]+)"', (ROOT/'packaging/ARISE.iss').read_text(encoding='utf-8')).group(1),
            'Bundle manifest': re.search(r"arise='([^']+)'", (ROOT/'scripts/Build-Bundle.ps1').read_text(encoding='utf-8')).group(1),
            'Release notes': re.search(r'^# ARISE ([0-9.]+) ', (ROOT/'packaging/RELEASE-NOTES.md').read_text(encoding='utf-8')).group(1),
        }
        for name, version in sources.items():
            with self.subTest(source=name):
                self.assertEqual(version, __version__, f'{name} must match the runtime, including versioned icon filenames')

    def test_versions_under_windows_legacy_default_encoding(self):
        original = Path.open
        def legacy_open(path, mode='r', buffering=-1, encoding=None, errors=None, newline=None):
            if 'b' not in mode and encoding in (None, 'locale'):
                encoding = 'cp1252'
            return original(path, mode, buffering, encoding, errors, newline)
        with patch.object(Path, 'open', legacy_open):
            self.test_shipped_versions_agree()
