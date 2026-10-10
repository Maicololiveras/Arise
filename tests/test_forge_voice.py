import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from arise_app.forge_voice import voice_command,ForgeConnection

class ForgeVoiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_local_connection_never_receives_cloud_key_and_forwards_audio(self):
        calls=[];events=[]
        class Process:
            def __init__(self,command,**kwargs):calls.append({k:v for k,v in kwargs.items() if k!='on_event'});self.event=kwargs['on_event']
            def request(self,request,timeout):
                calls.append(request)
                self.event({'type':'voice_event','event':{'type':'session.updated'}})
                return {'data':{}}
            def send(self,record):events.append(record)
            def close(self):pass
        runtime=SimpleNamespace(storage=SimpleNamespace(config={'workspace':'.'}),credentials=SimpleNamespace(get=lambda key:'cloud-secret' if key=='openai' else ''))
        with patch('arise_app.forge_voice.JsonProcess',Process),patch('arise_app.forge_voice.voice_command',return_value=['fixture']):
            async with ForgeConnection(runtime,'local','local-audio','ws://127.0.0.1:1236/v1/realtime') as connection:
                self.assertEqual(json.loads(await connection.recv())['type'],'session.updated')
                await connection.send(json.dumps({'type':'input_audio_buffer.append','audio':'AQACAA=='}))
        self.assertNotIn('cloud-secret',json.dumps(calls))
        self.assertEqual(events[0]['event']['audio'],'AQACAA==')
        self.assertEqual(calls[1]['config']['backend'],'local')

    async def test_old_forge_is_reported_instead_of_starting_another_engine(self):
        runtime=SimpleNamespace(storage=SimpleNamespace(config={'mcp':{'forge':{'enabled':True,'command':['node','/missing/dist/bin/forge-mcp-cli.js']}}}))
        with self.assertRaisesRegex(RuntimeError,'Actualiza Forge'):voice_command(runtime)
