"""Real Pi process + local model HTTP server + real ARISE extension bridge."""
import json
import os
import shutil
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from arise_app.assistant import Assistant
from arise_app.server import make_server

CLI = Path(os.environ.get("PI_TEST_CLI", Path(__file__).resolve().parents[1] / "vendor/node_modules/@earendil-works/pi-coding-agent/dist/cli.js"))

@unittest.skipUnless(CLI.is_file() and shutil.which("node"), "Pi real no está instalado; usar npm ci --prefix vendor")
class RealPiTests(unittest.TestCase):
    def test_real_pi_invokes_arise_extension_and_persists_memory(self):
        requests = []
        class Model(BaseHTTPRequestHandler):
            def log_message(self, *_): pass
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                requests.append(body)
                tool_messages = [m for m in body["messages"] if m.get("role") == "tool"]
                delta = {"role": "assistant"}
                if not tool_messages:
                    delta["tool_calls"] = [{"index": 0, "id": "call-memory", "type": "function", "function": {
                        "name": "arise_call", "arguments": json.dumps({"name": "memory.save", "arguments_json": json.dumps({"text": "Nota desde Pi real"})})}}]
                    finish = "tool_calls"
                else:
                    delta["content"] = "Nota guardada mediante ARISE."
                    finish = "stop"
                self.send_response(200); self.send_header("Content-Type", "text/event-stream"); self.end_headers()
                for chunk in ({"id": "fixture", "object": "chat.completion.chunk", "choices": [{"index": 0, "delta": delta, "finish_reason": None}]},
                              {"id": "fixture", "object": "chat.completion.chunk", "choices": [{"index": 0, "delta": {}, "finish_reason": finish}]}):
                    self.wfile.write(("data: " + json.dumps(chunk) + "\n\n").encode()); self.wfile.flush()
                self.wfile.write(b"data: [DONE]\n\n")
        model = ThreadingHTTPServer(("127.0.0.1", 0), Model)
        threading.Thread(target=model.serve_forever, daemon=True).start()
        with tempfile.TemporaryDirectory() as root:
            agent = Path(root) / "pi-agent"; agent.mkdir()
            (agent / "settings.json").write_text(json.dumps({"telemetry": False, "packages": []}))
            (agent / "models.json").write_text(json.dumps({"providers": {"arise-test": {
                "baseUrl": f"http://127.0.0.1:{model.server_port}/v1", "api": "openai-completions", "apiKey": "fixture-only",
                "models": [{"id": "arise-test", "input": ["text"], "reasoning": False, "contextWindow": 32000, "maxTokens": 4000}]
            }}}))
            runtime = Assistant(Path(root) / "arise")
            runtime.storage.config.update({"pi_command": [shutil.which("node"), str(CLI)], "pi_extra_args": ["--offline", "--no-extensions", "--no-skills", "--no-context-files", "--no-builtin-tools"],
                "agent_provider": "arise-test", "agent_model": "arise-test", "thinking": "off",
                "gentle_path": str(CLI.parents[3] / "gentle-pi")})
            bridge = make_server(runtime); threading.Thread(target=bridge.serve_forever, daemon=True).start()
            try:
                with patch.dict(os.environ, {"PI_CODING_AGENT_DIR": str(agent), "PI_OFFLINE": "1", "PI_TELEMETRY": "0"}):
                    task = runtime.prompt("Guarda una nota")["task_id"]
                self.assertTrue(runtime.settled.wait(20), "Pi no completó su ejecución")
                result = runtime.tasks[task]
                self.assertEqual(result["status"], "done", result)
                self.assertTrue(runtime.pi_state.get("gentleVerified"), "Gentle Shell no cargó sus comandos reales")
                self.assertIn("Nota guardada", result["output"])
                notes = json.loads(runtime.memory_path.read_text())
                self.assertEqual(notes[0]["text"], "Nota desde Pi real")
                self.assertEqual(len(requests), 2)
                self.assertIn("arise_call", [t["function"]["name"] for t in requests[0]["tools"]])
                self.assertEqual([m["role"] for m in runtime.storage.messages(runtime.conversation)], ["user", "assistant"])
            finally:
                runtime.close(); runtime.storage.db.close(); bridge.shutdown(); bridge.server_close()
        model.shutdown(); model.server_close()
