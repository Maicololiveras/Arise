import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from arise_app.assistant import Assistant
from arise_app.voice import wake_match, VoiceService
from scripts.patch_gentle import apply

class AssistantUpgradeTests(unittest.TestCase):
    def test_wake_aliases_are_greeting_scoped_and_keep_request_text(self):
        phrases = ['oye arise', 'hey arise', 'hola arise']
        for spoken in ('Oye, a raíz, Busca información de Bogotá', 'Hey Arise, Busca información de Bogotá', 'Hola arais Busca información de Bogotá'):
            self.assertEqual(wake_match(spoken, phrases), ('Busca información de Bogotá', True))
        for spoken in ('a raíz de la falla', 'ariseño'):
            self.assertFalse(wake_match(spoken, phrases)[1])
        self.assertFalse(wake_match('oye a raíz busca', ['computer'])[1])

    def test_message_is_visible_before_cold_start_and_retained_on_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Assistant(tmp)
            def cold_start():
                self.assertEqual(r.storage.messages(r.conversation)[-1]['text'], 'Hello')
                raise RuntimeError('cold start failed')
            try:
                with patch.object(r, 'connect_pi', side_effect=cold_start):
                    with self.assertRaisesRegex(RuntimeError, 'cold start failed'): r.prompt('Hello')
                self.assertFalse(r.busy)
            finally: r.close(); r.storage.db.close()

    def test_48_registry_is_never_overwritten(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root/'package.json').write_text(json.dumps({'name':'gentle-pi','version':'4.8.0'}))
            (root/'extensions').mkdir(); target=root/'extensions/skill-registry.ts';target.write_text('upstream')
            apply(root)
            self.assertEqual(target.read_text(),'upstream')
