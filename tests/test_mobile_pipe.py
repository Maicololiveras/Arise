import http.client
import json
import os
import struct
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from arise_app.assistant import Assistant
from arise_app.companion import Devices, mobile_handler
from arise_app.mobile_setup import TailNode
from arise_app.storage import Storage


class MobilePipeTests(unittest.TestCase):
    def test_paired_phone_resolves_desktop_approval_and_revocation_takes_effect(self):
        with tempfile.TemporaryDirectory() as root:
            storage = Storage(root)
            self.addCleanup(storage.db.close)
            chat = storage.create_conversation()
            gate = threading.Event()
            pending = dict(event=gate, approved=False, generation=0, chat=chat, action='create', preview='proposal')
            runtime = SimpleNamespace(storage=storage, devices=Devices(storage), conversation=chat,
                                      approvals={'request': pending}, lock=threading.RLock(), stop_generation=0,
                                      transition_lock=threading.RLock(), mobile_security=Mock())
            runtime.approve = lambda key, decision: Assistant.approve(runtime, key, decision)
            invite = runtime.devices.invite(chat)
            cookie = runtime.devices.pair(invite['code'], 'Phone',peer='phone-A')
            origin = 'https://arise-mobile.example.ts.net'
            node = TailNode.__new__(TailNode)
            read_request, send_request = os.pipe()
            read_response, send_response = os.pipe()
            with os.fdopen(read_request,'rb') as incoming, os.fdopen(send_request,'wb') as outgoing, \
                 os.fdopen(read_response,'rb') as replies, os.fdopen(send_response,'wb') as writer:
                node.process = Mock(stdout=incoming, stdin=writer, poll=Mock(return_value=None))
                node.handler = mobile_handler(runtime, origin)
                thread = threading.Thread(target=node.serve, daemon=True)
                thread.start()
                def request(method, path, data=None, peer="phone-A"):
                    body = json.dumps(data).encode() if data else b''
                    headers = [f'{method} {path} HTTP/1.1','Host: arise-mobile.example.ts.net',
                               'X-Arise-Tailnode: '+peer,'Origin: '+origin,'Cookie: arise_device='+cookie,'Content-Type: application/json',
                               'Content-Length: '+str(len(body))]
                    packet = ('\r\n'.join(headers)+'\r\n\r\n').encode()+body
                    outgoing.write(struct.pack('!I',len(packet))+packet)
                    outgoing.flush()
                    status = replies.readline()
                    headers = http.client.parse_headers(replies)
                    return int(status.split()[1]), json.loads(replies.read(int(headers['Content-Length'])))
                try:
                    self.assertEqual(request('GET','/messages',peer='phone-B')[0],401)
                    self.assertEqual(request('GET','/messages')[1]['approvals'][0]['id'],'request')
                    self.assertEqual(request('POST','/approval',dict(id='request',approved=True,otp='fixture'))[0],200)
                    runtime.mobile_security.verify.assert_called_once_with('fixture')
                    self.assertTrue(gate.is_set())
                    self.assertEqual(request('GET','/messages')[1]['approvals'],[])
                    self.assertEqual(request('POST','/approval',dict(id='request',approved=False))[0],400)
                    device=runtime.devices.authorize(cookie,"phone-A")
                    runtime.devices.revoke(chat,device['id'])
                    self.assertEqual(request('GET','/agents')[0],401)
                finally:
                    outgoing.close()
                    thread.join(3)
                    self.assertFalse(thread.is_alive())
