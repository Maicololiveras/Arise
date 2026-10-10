import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from arise_app.discovery import detect, detect_gentle_installation

class RecoveryTests(unittest.TestCase):
    def test_recovered_installation_replaces_stale_global_paths(self):
        recovered = dict(pi_command=['node','owned/cli.js'],gentle_path='owned/gentle',gentle_agent_home='owned/home',gentle_channel='main')
        with patch('arise_app.discovery.detect_gentle_installation',return_value=recovered):
            found=detect(dict(pi_command=['old'],gentle_path='old',gentle_agent_home=''))
        self.assertEqual(found['pi_command'],recovered['pi_command'])
        self.assertEqual(found['gentle_agent_home'],'owned/home')

    def test_existing_explicit_home_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as tmp, patch('arise_app.discovery.detect_gentle_installation') as probe:
            detect(dict(pi_command=['missing-pi'],gentle_agent_home=tmp))
            probe.assert_not_called()

    def test_failed_probe_does_not_adopt_partial_installation(self):
        responses=[SimpleNamespace(returncode=0,stdout=json.dumps([{'dependencies':{'gentle-pi':{'path':'fixture'}}}])),SimpleNamespace(returncode=1,stdout='')]
        with patch('arise_app.discovery.shutil.which',side_effect=lambda x:x),patch('arise_app.discovery.gentle_valid',return_value=True),patch('arise_app.discovery.subprocess.run',side_effect=responses):
            self.assertIsNone(detect_gentle_installation())
