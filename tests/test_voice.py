"""Actual local WebSocket transports with simulated provider responses. No cloud credentials."""
import asyncio
import base64
import json
import tempfile
import threading
import unittest
from pathlib import Path
from websockets.asyncio.server import serve
from websockets.asyncio.client import connect
from arise_app.assistant import Assistant
from arise_app.voice import VoiceSession

class FakeAudio:
    def __init__(self): self.speaking=False; self.played=[]
    def read(self): return None
    def play(self, pcm, rate=24000, item_id=None): self.played.append(pcm); self.speaking=True
    def interrupt(self): self.speaking=False; return {"item_id": "item-1", "audio_end_ms": 20}

class VoiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.r=Assistant(self.temp.name); self.audio=FakeAudio(); self.active=threading.Event(); self.active.set()
        self.r.storage.config.update({"voice_provider":"openai","voice_model":"fixture-realtime","voice":"marin"})
    async def asyncTearDown(self): self.r.close(); self.r.storage.db.close(); self.temp.cleanup()

    async def test_openai_websocket_handshake_audio_interrupt_and_delegation(self):
        self.r.credentials.save("openai", "fixture-only", False)
        records=[]
        async def provider(ws):
            setup=json.loads(await ws.recv()); records.append(setup)
            await ws.send(json.dumps({"type":"session.updated"}))
            await ws.send(json.dumps({"type":"response.output_audio.delta","delta":base64.b64encode(b"\x01\x00"*20).decode(),"item_id":"item-1"}))
            await ws.send(json.dumps({"type":"input_audio_buffer.speech_started"}))
            truncate=json.loads(await ws.recv()); records.append(truncate)
            await ws.send(json.dumps({"type":"response.function_call_arguments.done","call_id":"call-stop","name":"stop_task","arguments":"{}"}))
            records.append(json.loads(await ws.recv())); records.append(json.loads(await ws.recv()))
            self.active.clear()
        async with serve(provider,"127.0.0.1",0) as server:
            url=f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}"
            session=VoiceSession(self.r,self.audio,self.active,connect=lambda *a,**kw:connect(url))
            await asyncio.wait_for(session.run(),5)
        self.assertEqual(records[0]["session"]["type"],"realtime")
        self.assertEqual(records[1]["type"],"conversation.item.truncate")
        self.assertEqual(records[1]["audio_end_ms"],20)
        result=json.loads(records[2]["item"]["output"]); self.assertTrue(result["stopped"])
        self.assertEqual(records[3]["type"],"response.create")
        self.assertEqual(len(self.audio.played),1)

    async def test_gemini_websocket_audio_and_tool_response(self):
        self.r.storage.config.update({"voice_provider":"gemini","voice_model":"fixture-live","voice":"Aoede"})
        self.r.credentials.save("gemini","fixture-only",False)
        records=[]
        async def provider(ws):
            records.append(json.loads(await ws.recv())); await ws.send(json.dumps({"setupComplete":{}}))
            await ws.send(json.dumps({"serverContent":{"modelTurn":{"parts":[{"inlineData":{"mimeType":"audio/pcm;rate=24000","data":base64.b64encode(b"\x01\x00"*20).decode()}}]}}}))
            await ws.send(json.dumps({"toolCall":{"functionCalls":[{"id":"stop","name":"stop_task","args":{}}]}}))
            records.append(json.loads(await ws.recv())); self.active.clear()
        async with serve(provider,"127.0.0.1",0) as server:
            url=f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}"
            session=VoiceSession(self.r,self.audio,self.active,connect=lambda *a,**kw:connect(url))
            await asyncio.wait_for(session.run(),5)
        self.assertEqual(records[0]["setup"]["model"],"models/fixture-live")
        self.assertTrue(records[1]["toolResponse"]["functionResponses"][0]["response"]["stopped"])
        self.assertEqual(len(self.audio.played),1)

    async def test_duplicate_tool_call_executes_once(self):
        session=VoiceSession(self.r,self.audio,self.active)
        class Socket:
            def __init__(self): self.sent=[]
            async def send(self,value):self.sent.append(json.loads(value))
        session.ws=Socket()
        await session.call("same","stop_task",{})
        await session.call("same","stop_task",{})
        self.assertEqual(len(session.ws.sent),2)

    async def test_provider_rejection_never_becomes_connected(self):
        self.r.credentials.save("openai","fixture-only",False)
        async def provider(ws):
            await ws.recv();await ws.send(json.dumps({"type":"error","error":{"message":"Invalid model"}}))
        async with serve(provider,"127.0.0.1",0) as server:
            url=f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}"
            session=VoiceSession(self.r,self.audio,self.active,connect=lambda *a,**kw:connect(url))
            with self.assertRaisesRegex(RuntimeError,"configurar"):await session.run()
        self.assertNotEqual(self.r.orb.value.state,"listening")
