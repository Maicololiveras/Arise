import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch
from arise_app.processes import JsonProcess, McpClient
from arise_app.runtime import Runtime
from arise_app.server import make_server
from arise_app.storage import Storage, Vault
from arise_app.gmail import Gmail

FIXTURE = [sys.executable, str(Path(__file__).with_name("fake_agent.py"))]


class ProtocolTests(unittest.TestCase):
    def test_mcp_initialize_and_real_catalog(self):
        client = McpClient(FIXTURE)
        try:
            self.assertEqual(client.tools[0]["name"], "echo")
            result = client.call("echo", {"text": "mañana\u2028fin"})
            self.assertEqual(json.loads(result["content"][0]["text"])["text"], "mañana\u2028fin")
            with self.assertRaises(ValueError):
                client.call("imaginary_tool", {})
        finally:
            client.close()

    def test_rpc_correlates_concurrent_requests(self):
        rpc = JsonProcess(FIXTURE)
        try:
            output = []
            threads = [threading.Thread(target=lambda: output.append(rpc.request({"type": "get_state"}))) for _ in range(8)]
            for thread in threads: thread.start()
            for thread in threads: thread.join()
            self.assertEqual(len(output), 8)
            self.assertEqual(len({r["id"] for r in output}), 8)
        finally:
            rpc.close()


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.runtime = Runtime(self.temp.name)
        self.runtime.storage.config["pi_command"] = FIXTURE
        self.runtime.url = "http://127.0.0.1:9999"

    def tearDown(self):
        self.runtime.close()
        self.runtime.storage.db.close()
        self.temp.cleanup()

    def wait_task(self, identity):
        for _ in range(100):
            if self.runtime.tasks[identity]["status"] != "running": return self.runtime.tasks[identity]
            time.sleep(.02)
        self.fail("Task did not settle")

    def test_chat_end_to_end_against_protocol_fixture(self):
        identity = self.runtime.prompt("hola")['task_id']
        task = self.wait_task(identity)
        self.assertEqual(task["status"], "done")
        self.assertEqual(task["output"], "Respuesta\u2028hola")
        messages = self.runtime.storage.messages(self.runtime.conversation)
        self.assertEqual([m["role"] for m in messages], ["user", "assistant"])
        self.assertNotIn("PRIVATE THINKING", json.dumps(self.runtime.events_after(0)))

    def test_agent_end_is_not_completion(self):
        self.runtime.busy = True
        self.runtime.pi_event({"type": "agent_end", "willRetry": False})
        self.assertTrue(self.runtime.busy)
        self.runtime.pi_event({"type": "agent_settled"})
        self.assertFalse(self.runtime.busy)

    def test_cancel_then_send_second_message(self):
        first = self.runtime.prompt("wait")["task_id"]
        self.runtime.stop()
        self.assertEqual(self.runtime.tasks[first]["status"], "error")
        second = self.runtime.prompt("segundo")["task_id"]
        task = self.wait_task(second)
        self.assertEqual(task["output"], "Respuesta\u2028segundo")
        time.sleep(.45)
        self.assertEqual(self.runtime.tasks[second]["output"], "Respuesta\u2028segundo")

    def test_conversation_history_isolated(self):
        original = self.runtime.conversation
        self.runtime.storage.message(original, "user", "uno")
        second = self.runtime.switch_conversation()["id"]
        self.runtime.storage.message(second, "user", "dos")
        self.assertEqual(self.runtime.switch_conversation(original)["messages"][0]["text"], "uno")

    def test_scoped_files_traversal_and_symlink(self):
        outside = Path(self.temp.name) / "secret.txt"
        outside.write_text("hidden")
        with self.assertRaises(ValueError): self.runtime.call_tool("files.read", {"path": "../secret.txt"})
        link = Path(self.runtime.storage.config["workspace"]) / "link"
        try: link.symlink_to(outside)
        except OSError: return
        with self.assertRaises(ValueError): self.runtime.call_tool("files.read", {"path": "link"})

    def test_memory_persists_without_provider(self):
        self.runtime.call_tool("memory.save", {"text": "Prefiero español."})
        result = self.runtime.call_tool("memory.search", {"query": "español"})
        self.assertEqual(json.loads(result["content"][0]["text"])["notes"][0]["text"], "Prefiero español.")

    def test_desktop_requires_ui_enable(self):
        self.runtime.mcp["inputcontrol"] = McpClient(FIXTURE)
        with self.assertRaises(RuntimeError): self.runtime.call_tool("inputcontrol.echo", {})



    def test_gmail_cannot_send(self):
        with self.assertRaisesRegex(ValueError, "solo permite"): self.runtime.call_tool("gmail.send", {})

    def test_gmail_draft_uses_draft_endpoint(self):
        with patch.object(self.runtime.gmail, "request", return_value={"id": "draft-1"}) as request:
            self.assertFalse(self.runtime.gmail.draft("user@example.com", "Hola", "Texto")["sent"])
            self.assertEqual(request.call_args.args[0], "drafts")
            with self.assertRaises(ValueError): self.runtime.gmail.draft("x\r\nBcc: y", "Subject", "Body")

    def test_bom_config_from_powershell_loads(self):
        path = Path(self.temp.name) / "settings.json"
        path.write_text(json.dumps(self.runtime.storage.config), encoding="utf-8-sig")
        other = Storage(self.temp.name)
        self.assertEqual(other.config["pi_command"], FIXTURE)
        other.db.close()


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.runtime = Runtime(self.temp.name)
        self.server = make_server(self.runtime)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.runtime.close()
        self.runtime.storage.db.close(); self.temp.cleanup()

    def get(self, path, headers=None, body=None):
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(self.runtime.url + path, data=data, headers=headers or {})
        return urllib.request.urlopen(request, timeout=3)

    def test_api_requires_session_token(self):
        with self.assertRaises(urllib.error.HTTPError) as caught: self.get("/api/status")
        self.assertEqual(caught.exception.code, 401)
        with self.get("/api/status", {"Authorization": "Bearer " + self.runtime.token}) as result:
            self.assertEqual(json.load(result)["version"], "0.2.0")

    def test_host_and_cross_origin_denied(self):
        for headers in ({"Host": "evil.example"}, {"Origin": "https://evil.example"}):
            with self.assertRaises(urllib.error.HTTPError) as caught: self.get("/api/status", headers)
            self.assertEqual(caught.exception.code, 403)


    def test_post_json_memory_journey(self):
        headers = {"Authorization": "Bearer " + self.runtime.token, "Content-Type": "application/json"}
        with self.get("/api/tools/call", headers, {"name": "memory.save", "arguments": {"text": "nota HTTP"}}) as result:
            self.assertFalse(json.load(result)["isError"])
        with self.get("/api/tools/call", headers, {"name": "memory.search", "arguments": {"query": "HTTP"}}) as result:
            content = json.load(result)["content"][0]["text"]
            self.assertEqual(json.loads(content)["notes"][0]["text"], "nota HTTP")


if __name__ == "__main__": unittest.main()
