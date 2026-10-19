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

    async def test_old_voice_cannot_dispatch_or_speak_after_chat_switch_and_return(self):
        session=VoiceSession(self.r,self.audio,self.active)
        original=self.r.conversation
        self.r.switch_conversation();self.r.switch_conversation(original)
        with self.assertRaisesRegex(RuntimeError,"cambió"):
            await session.delegate("delegate_task",{"instruction":"No ejecutar"})
        await session.openai_event({"type":"response.output_audio.delta","delta":base64.b64encode(b"12").decode()})
        self.assertEqual(self.audio.played,[])

    def make_session(self):
        session=VoiceSession(self.r,self.audio,self.active)
        class Socket:
            def __init__(self): self.sent=[]
            async def send(self,value): self.sent.append(json.loads(value))
        session.ws=Socket()
        return session

    def install_task(self, identity="job", conversation=None, status="running"):
        self.r.tasks[identity]={"id":identity,"conversation":conversation or self.r.conversation,
            "status":status,"output":"Documento verificado","error":""}
        self.r.current_task=identity if status=="running" else None
        self.r.busy=status=="running"

    async def test_acceptance_returns_before_completion_and_does_not_block_conversation(self):
        from unittest.mock import patch
        session=self.make_session()
        def submit(text):
            self.install_task()
            return {"task_id":"job"}
        with patch.object(self.r,"prompt",side_effect=submit) as prompt:
            await asyncio.wait_for(session.call("submit","delegate_task",{"instruction":"Crear Word"}),1)
            await session.call("submit","delegate_task",{"instruction":"Crear Word"})
            prompt.assert_called_once()
        result=json.loads(session.ws.sent[0]["item"]["output"])
        self.assertEqual(result["status"],"accepted")
        self.assertTrue(self.r.busy)
        await session.openai_event({"type":"response.output_audio.delta","delta":base64.b64encode(b"12").decode()})
        self.assertEqual(self.audio.played,[b"12"])
        status=await session.delegate("task_status",{"task_id":"job"})
        self.assertEqual(status["status"],"running")
        self.assertEqual(status["result"],"")
        self.r.busy=False

    async def test_new_task_is_not_silently_steered_and_explicit_correction_is_scoped(self):
        from unittest.mock import patch
        self.install_task()
        session=self.make_session()
        with patch.object(self.r,"steer",return_value={"task_id":"job"}) as steer:
            self.assertEqual((await session.delegate("delegate_task",{"instruction":"Otra tarea"}))["status"],"busy")
            steer.assert_not_called()
            await session.delegate("steer_task",{"task_id":"job","instruction":"Usa plantilla WEG"})
            steer.assert_called_once_with("Usa plantilla WEG")
        self.install_task("foreign",conversation="other")
        for name in ("task_status","steer_task","cancel_task"):
            with self.assertRaises(ValueError):
                await session.delegate(name,{"task_id":"foreign","instruction":"No"})
        self.r.busy=False

    async def test_completion_is_announced_once_when_idle_and_never_after_chat_change(self):
        for provider in ("openai","gemini"):
            self.r.storage.config["voice_provider"]=provider
            session=self.make_session();self.install_task(status="done")
            session.watched_tasks.add("job");session.last_activity=0
            session.response_active=True
            await session.notify_finished();self.assertEqual(session.ws.sent,[])
            session.response_active=False
            await session.notify_finished();self.assertTrue(session.ws.sent)
            count=len(session.ws.sent)
            await session.notify_finished();self.assertEqual(len(session.ws.sent),count)
            session.watched_tasks.add("job");session.last_activity=0;session.response_active=False
            self.r.chat_generation+=1
            await session.notify_finished();self.assertEqual(len(session.ws.sent),count)

    async def test_cancel_does_not_touch_a_different_task_and_stop_revokes_pending_dispatch(self):
        from unittest.mock import patch
        session=self.make_session();self.install_task()
        self.r.tasks["old"]={"id":"old","conversation":self.r.conversation,"status":"done","output":"","error":""}
        with patch.object(self.r,"stop") as stop:
            with self.assertRaises(ValueError):await session.delegate("cancel_task",{"task_id":"old"})
            stop.assert_not_called()
            await session.delegate("cancel_task",{"task_id":"job"})
            stop.assert_called_once()
        generation=self.r.stop_generation;self.r.stop_generation+=1
        with self.assertRaisesRegex(RuntimeError,"parada"):
            session._dispatch_to_chat("delegate_task",{"instruction":"No ejecutar"},generation)
        self.r.busy=False

    async def test_result_does_not_interrupt_microphone_and_error_is_not_raw_diagnostic(self):
        session=self.make_session();self.install_task(status="error")
        self.r.tasks["job"]["error"]="secret backend diagnostic"
        session.watched_tasks.add("job");session.last_activity=0
        session.input_quiet_after=float("inf")
        await session.notify_finished();self.assertEqual(session.ws.sent,[])
        session.input_quiet_after=0
        await session.notify_finished()
        self.assertNotIn("secret backend",json.dumps(session.ws.sent))
        self.assertIn('has_error',json.dumps(session.ws.sent))


class VoiceStartupTests(unittest.TestCase):
    def test_device_failure_is_not_reported_as_missing_model_or_provider(self):
        from arise_app.voice import VoiceService
        from unittest.mock import Mock
        runtime=Mock(); runtime.storage.config={'input_device':None,'output_device':None}
        audio=Mock(); audio.open.side_effect=OSError('fixture private provider text')
        service=VoiceService(runtime,audio_factory=lambda *args:audio)
        with self.assertRaisesRegex(RuntimeError,'antes de cargar el modelo') as error:
            service._ensure_audio()
        self.assertNotIn('fixture private',str(error.exception))
        audio.close.assert_called_once()
        self.assertIsNone(service.audio)

    def test_empty_model_directory_is_not_considered_ready(self):
        from arise_app.voice import VoiceService
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as root:
            runtime=Mock(); runtime.storage.config={'wake_model':root}
            service=VoiceService(runtime)
            with self.assertRaisesRegex(RuntimeError,'modelo Vosk válido'):
                service._load_wake()

    def test_native_device_stages_keep_only_numeric_backend_code(self):
        import sys
        from unittest.mock import Mock,patch
        from arise_app.audio import Audio,AudioDeviceError
        for stage in ('input','output'):
            sd=Mock()
            error=Exception('private backend diagnostic',-9997)
            if stage=='input':sd.RawInputStream.side_effect=error
            else:sd.RawOutputStream.side_effect=error
            with patch.dict(sys.modules,{'sounddevice':sd}):
                with self.assertRaises(AudioDeviceError) as raised:Audio().open()
            message=str(raised.exception)
            self.assertIn('micrófono' if stage=='input' else 'salida',message)
            self.assertIn('-9997',message)
            self.assertNotIn('private',message)
