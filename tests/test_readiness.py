import json
import socket
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from unittest.mock import patch
from arise_app.diagnostics import checked_run
from arise_app.model_service import ModelService
from arise_app.processes import JsonProcess
from arise_app.runtime import Runtime


class ReadinessTests(unittest.TestCase):
    def test_exit_diagnostics_are_safe_and_reach_waiting_requests(self):
        events = []
        rpc = JsonProcess([sys.executable, '-c',
            "import sys,time; time.sleep(.1); print('EPIPE secret-token-value',file=sys.stderr); sys.exit(7)"], on_event=events.append)
        try:
            with self.assertRaisesRegex(RuntimeError, 'EPIPE') as failure:
                rpc.request({'type': 'get_state'}, timeout=3)
            self.assertNotIn('secret-token-value', str(failure.exception))
            self.assertTrue(rpc.diagnostics.done.wait(1))
        finally:
            rpc.close()

    def test_failed_pi_cannot_respawn_on_every_voice_utterance(self):
        with tempfile.TemporaryDirectory() as root:
            runtime = Runtime(root)
            runtime.pi_event({'type': 'process_closed', 'diagnostic': 'EPIPE'})
            try:
                with patch('arise_app.runtime.JsonProcess') as spawn:
                    for _ in range(5):
                        with self.assertRaisesRegex(RuntimeError, 'pausado'):
                            runtime.connect_pi()
                    spawn.assert_not_called()
                runtime.settings({})
                self.assertEqual(runtime.pi_retry_after, 0)
            finally:
                runtime.close()
                runtime.storage.db.close()

    def test_pip_failure_reports_category_without_credentials(self):
        with self.assertRaisesRegex(RuntimeError, 'TLS') as failure:
            checked_run([sys.executable, '-c', "import sys; print('CERTIFICATE_VERIFY_FAILED https://secret:password@host'); sys.exit(1)"], 'pip')
        self.assertNotIn('password', str(failure.exception))

    def test_managed_server_waits_for_catalog_and_stops_owned_process(self):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        script = '''import time
from http.server import BaseHTTPRequestHandler,HTTPServer
time.sleep(.2)
class H(BaseHTTPRequestHandler):
 def log_message(self,*a): pass
 def do_GET(self):
  self.send_response(200); self.end_headers(); self.wfile.write(b'{"data":[{"id":"test-model"}]}')
HTTPServer(('127.0.0.1',PORT),H).serve_forever()
'''.replace('PORT',str(port))
        def probe():
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/v1/models', timeout=.2) as response:
                return json.load(response)
        service = ModelService()
        try:
            data = service.ensure(probe, [sys.executable, '-c', script], timeout=4)
            self.assertEqual(data['data'][0]['id'], 'test-model')
            process = service.process.process
            service.ensure(probe, [sys.executable, '-c', script], timeout=4)
            self.assertIs(service.process.process, process)
            self.assertEqual(service.snapshot()['state'], 'ready')
        finally:
            service.close()
        self.assertIsNotNone(process.poll())

    def test_reuses_external_server_without_spawning_or_owning_it(self):
        service = ModelService()
        with patch('arise_app.model_service.JsonProcess') as spawn:
            service.ensure(lambda: {'data': [{'id':'external'}]}, ['unused'])
            spawn.assert_not_called()
            self.assertFalse(service.snapshot()['managed'])
            service.close()

    def test_empty_catalog_is_not_ready_and_status_never_waits_for_startup(self):
        service = ModelService()
        errors = []
        def start():
            try: service.ensure(lambda: {'data': []}, [], timeout=5)
            except RuntimeError as error: errors.append(str(error))
        thread = threading.Thread(target=start)
        thread.start()
        time.sleep(.05)
        began = time.monotonic()
        self.assertEqual(service.snapshot()['state'], 'starting')
        self.assertLess(time.monotonic()-began,.2)
        service.close()
        thread.join(1)
        self.assertFalse(thread.is_alive())
        self.assertTrue(errors)
