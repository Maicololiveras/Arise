"""Catch installer/runtime drift before the expensive Windows packaging smoke."""
from pathlib import Path
import re
import tomllib
import unittest
from arise_app import __version__

ROOT = Path(__file__).resolve().parents[1]

class ReleaseVersionTests(unittest.TestCase):
    def test_shipped_versions_agree(self):
        sources = {
            'Python package': tomllib.loads((ROOT/'pyproject.toml').read_text())['project']['version'],
            'Inno installer': re.search(r'^#define AppVersion "([^"]+)"', (ROOT/'packaging/ARISE.iss').read_text()).group(1),
            'Bundle manifest': re.search(r"arise='([^']+)'", (ROOT/'scripts/Build-Bundle.ps1').read_text()).group(1),
            'Release notes': re.search(r'^# ARISE ([0-9.]+) ', (ROOT/'packaging/RELEASE-NOTES.md').read_text()).group(1),
        }
        for name, version in sources.items():
            with self.subTest(source=name):
                self.assertEqual(version, __version__, f'{name} must match the runtime, including versioned icon filenames')
