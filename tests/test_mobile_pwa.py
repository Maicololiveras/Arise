from pathlib import Path
import shutil
import subprocess
import unittest


class MobilePWATests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node is required for browser event tests')
    def test_install_prompt_lifecycle(self):
        root = Path(__file__).resolve().parents[1]
        subprocess.run([shutil.which('node'), 'tests/companion-install.test.cjs'],
                       cwd=root, check=True, capture_output=True, timeout=10)
