import base64
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from email import policy
from email.parser import BytesParser
from pathlib import Path
from unittest.mock import patch
from arise_app.assistant import Assistant
from arise_app.voice import VoiceService, wake_match
from arise_app.audio import Audio, resample

FIXTURE = [sys.executable, str(Path(__file__).with_name("fake_agent.py"))]

class AssistantTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.r = Assistant(self.temp.name)
        self.r.storage.config["pi_command"] = FIXTURE
        self.r.url = "http://127.0.0.1:9999"
    def tearDown(self):
        self.r.close(); self.r.storage.db.close(); self.temp.cleanup()

    def test_file_write_read_and_path_boundary(self):
        self.r.call_tool("files.write", {"path": "docs/hello.txt", "text": "Hola ARISE"})
        result = self.r.call_tool("files.read", {"path": "docs/hello.txt"})
        self.assertEqual(json.loads(result["content"][0]["text"])["text"], "Hola ARISE")
        with self.assertRaises(ValueError): self.r.call_tool("files.write", {"path": "../outside.txt", "text": "blocked"})

    def test_credentials_session_never_written_to_config_or_events(self):
        self.r.credentials.save("openai", "test-not-a-real-key", persist=False)
        self.assertEqual(self.r.credentials.get("openai"), "test-not-a-real-key")
        text = self.r.storage.config_path.read_text() + json.dumps(self.r.events_after(0))
        self.assertNotIn("test-not-a-real-key", text)

    def test_gmail_attachment_roundtrip(self):
        self.r.call_tool("files.write", {"path": "report.txt", "text": "Contenido adjunto"})
        with patch.object(self.r.gmail, "request", return_value={"id": "draft-1"}) as request:
            self.r.call_tool("gmail.draft", {"to": "user@example.com", "subject": "Informe", "body": "Adjunto", "attachments": ["report.txt"]})
            raw = request.call_args.args[1]["message"]["raw"]
            message = BytesParser(policy=policy.default).parsebytes(base64.urlsafe_b64decode(raw))
            attachment = next(message.iter_attachments())
            self.assertEqual(attachment.get_filename(), "report.txt")
            self.assertEqual(attachment.get_payload(decode=True).decode(), "Contenido adjunto")

    def approve_next(self, allow):
        def respond():
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                for event in self.r.events_after(0)["events"]:
                    if event["kind"] == "approval" and event["data"]["id"] in self.r.approvals:
                        self.r.approve(event["data"]["id"], allow); return
                time.sleep(.01)
        thread = threading.Thread(target=respond); thread.start(); return thread

    def test_send_requires_approval_and_is_not_replayed(self):
        with patch.object(self.r.gmail, "draft_preview", return_value={"to": "user@example.com"}), patch.object(self.r.gmail, "send_draft", return_value={"sent": True}) as send:
            t = self.approve_next(True)
            self.r.call_tool("gmail.send_draft", {"draft_id": "draft-1"}); t.join()
            t = self.approve_next(True)
            with self.assertRaisesRegex(RuntimeError, "intento"):
                self.r.call_tool("gmail.send_draft", {"draft_id": "draft-1"})
            t.join(); self.assertEqual(send.call_count, 1)

    def test_denied_send_has_no_side_effect(self):
        with patch.object(self.r.gmail, "draft_preview", return_value={}), patch.object(self.r.gmail, "send_draft") as send:
            t = self.approve_next(False)
            with self.assertRaises(RuntimeError): self.r.call_tool("gmail.send_draft", {"draft_id": "draft-2"})
            t.join(); send.assert_not_called()

    def test_stop_releases_pending_approval_and_revokes_control(self):
        errors = []
        self.r.desktop = True
        thread = threading.Thread(target=lambda: self.approval_wait(errors))
        thread.start()
        for _ in range(100):
            if self.r.approvals: break
            time.sleep(.01)
        self.r.stop(); thread.join(2)
        self.assertFalse(thread.is_alive()); self.assertFalse(self.r.desktop)
        self.assertEqual(len(errors), 1)

    def approval_wait(self, errors):
        try: self.r.ask_approval("send", {}, 10)
        except RuntimeError as e: errors.append(str(e))

    def test_settings_reject_invalid_provider_and_size(self):
        for changes in ({"voice_provider": "text-only"}, {"orb_size": 1}, {"wake_enabled": "false"}):
            with self.assertRaises(ValueError): self.r.settings(changes)

    def test_state_tracks_task_and_releases_capture_indicator(self):
        self.r.orb.update("working", screen=True)
        self.assertTrue(self.r.status()["orb"]["screen"])
        self.r.stop()
        self.assertFalse(self.r.status()["orb"]["screen"])
        self.assertFalse(self.r.status()["orb"]["control"])

    def test_voice_constructor_opens_no_microphone(self):
        with patch("arise_app.voice.Audio.open") as opened:
            voice = VoiceService(self.r)
            voice.mute(True); self.assertFalse(voice.wake())
            opened.assert_not_called()

class AudioTests(unittest.TestCase):
    def test_wake_boundary_and_payload(self):
        self.assertEqual(wake_match("Oye Arise abre notas", ["oye arise"]), ("abre notas", True))
        self.assertFalse(wake_match("oye arisearchitecture", ["oye arise"])[1])

    def test_resample_and_interruption_playback_position(self):
        pcm = (b"\x01\x00") * 320
        self.assertEqual(len(resample(pcm, 16000, 24000)), 960)
        audio = Audio(); audio.play(resample(pcm, 16000, 24000), item_id="item-1")
        target = bytearray(480); audio._playback(target, 240, None, None)
        result = audio.interrupt()
        self.assertEqual(result, {"item_id": "item-1", "audio_end_ms": 10})
        self.assertFalse(audio.buffers)

    def test_capture_bound_and_muted_capture(self):
        audio = Audio()
        for _ in range(200): audio._capture(b"a" * 640, 320, None, None)
        self.assertEqual(audio.incoming.qsize(), 150)
        self.assertEqual(audio.dropped, 50)
        audio.clear_input(); audio.muted = True; audio._capture(b"a" * 640, 320, None, None)
        self.assertEqual(audio.incoming.qsize(), 0)
