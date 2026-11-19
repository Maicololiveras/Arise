import unittest
from threading import RLock
from types import SimpleNamespace
from unittest.mock import Mock
from arise_app.runtime import Runtime


class AgentPickerTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.state = dict(model=dict(provider="a", id="one"), thinkingLevel="low")
        def request(record):
            self.calls.append(record["type"])
            if record["type"] == "get_available_models":
                return {"data":{"models":[{"provider":"b","id":"two"}]}}
            if record["type"] == "get_available_thinking_levels":
                return {"data":{"levels":["low","high"]}}
            if record["type"] == "set_model":
                self.state["model"] = dict(provider=record["provider"], id=record["modelId"])
            if record["type"] == "set_thinking_level":
                self.state["thinkingLevel"] = record["level"]
            return {"data":self.state}
        self.r = SimpleNamespace(transition_lock=RLock(), conversation="chat", busy=False,
            connect_pi=Mock(), pi=SimpleNamespace(request=request), pi_state={"gentleVerified":True},
            sessions=Mock(), storage=SimpleNamespace(config={},save_config=Mock()),session_command=Mock())

    def test_applies_live_and_saves_confirmed_state_for_chat(self):
        for kind, choice in (("model",["b","two"]),("effort","high")):
            result = Runtime.agent_picker(self.r,"chat",kind,choice)
            self.assertEqual(result["current"], choice)
        self.r.storage.save_config.assert_called_with(dict(agent_provider="b",agent_model="two",thinking="high"))
        self.r.sessions.save_preferences.assert_called_with("chat")
        self.assertTrue(self.r.pi_state["gentleVerified"])

    def test_no_write_on_stale_chat_busy_or_unavailable_effort(self):
        with self.assertRaises(RuntimeError): Runtime.agent_picker(self.r,"other","profile")
        self.r.busy=True
        with self.assertRaises(RuntimeError): Runtime.agent_picker(self.r,"chat","model")
        self.r.busy=False
        with self.assertRaises(ValueError): Runtime.agent_picker(self.r,"chat","effort","unknown")
        self.assertEqual(self.calls,["get_available_thinking_levels"])
        self.r.storage.save_config.assert_not_called()
        Runtime.agent_picker(self.r,"chat","profile")
        self.r.session_command.assert_called_once_with("/gentle:profiles")
