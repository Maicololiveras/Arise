import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from arise_app.daemon import read_descriptor, ping
from arise_app.remote import RemoteAssistant
from arise_app.assistant import Assistant
from arise_app.discovery import detect, import_mcp

class DaemonTests(unittest.TestCase):
    def test_separate_daemon_survives_client_close_and_stops_cleanly(self):
        with tempfile.TemporaryDirectory() as root:
            process = subprocess.Popen([sys.executable, "-m", "arise_app.daemon", "--data-dir", root, "--no-audio"],
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            try:
                descriptor = None
                for _ in range(100):
                    descriptor = read_descriptor(root)
                    if ping(descriptor): break
                    if process.poll() is not None: self.fail("Daemon failed: " + process.stderr.read().decode())
                    time.sleep(.05)
                self.assertTrue(ping(descriptor))
                remote = RemoteAssistant(descriptor, root)
                remote.call_tool("memory.save", {"text": "Persistente sin panel"})
                remote.close()
                self.assertIsNone(process.poll())
                other = RemoteAssistant(descriptor, root)
                result = other.call_tool("memory.search", {"query": "Persistente"})
                self.assertEqual(json.loads(result["content"][0]["text"])["notes"][0]["text"], "Persistente sin panel")
                other.shutdown(); self.assertEqual(process.wait(timeout=8), 0)
                self.assertFalse(Path(root, "daemon.json").exists())
            finally:
                if process.poll() is None: process.terminate(); process.wait(5)
                process.stderr.close()

    def test_incomplete_tasks_are_not_replayed_after_restart(self):
        with tempfile.TemporaryDirectory() as root:
            r = Assistant(root)
            r.persist_task({"id": "interrupted", "status": "running", "output": "", "error": ""})
            r.close(); r.storage.db.close()
            restarted = Assistant(root)
            try:
                self.assertEqual(restarted.tasks["interrupted"]["status"], "error")
                self.assertIn("Verifica", restarted.tasks["interrupted"]["error"])
                self.assertIsNone(restarted.pi)
            finally: restarted.close(); restarted.storage.db.close()

class DiscoveryTests(unittest.TestCase):
    def test_detects_gentle_from_existing_pi_settings_without_running_package(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root) / "gentle"; folder.mkdir(); (folder / "extensions").mkdir()
            (folder / "package.json").write_text(json.dumps({"name": "gentle-pi"}))
            (Path(root) / "settings.json").write_text(json.dumps({"packages": [str(folder)]}))
            result = detect({"pi_command": [sys.executable]}, root)
            self.assertEqual(Path(result["gentle_path"]), folder.resolve())
            self.assertEqual(result["pi_command"], [sys.executable])

    def test_imports_stdio_mcp_and_rejects_embedded_secrets(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "mcp.json"
            path.write_text(json.dumps({"mcpServers": {"notes": {"command": "python", "args": ["notes.py"]}}}))
            self.assertEqual(import_mcp(path)["notes"]["command"], ["python", "notes.py"])
            path.write_text(json.dumps({"mcpServers": {"notes": {"command": "python", "env": {"KEY": "secret"}}}}))
            with self.assertRaises(ValueError): import_mcp(path)
