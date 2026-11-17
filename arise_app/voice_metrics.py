"""Content-free, monotonic local voice timings. No audio or text is recorded."""
from contextlib import contextmanager
from contextvars import ContextVar
import time
import uuid

_current = ContextVar("voice_trace", default=None)

class VoiceTrace:
    def __init__(self, runtime):
        self.runtime = runtime
        self.id = uuid.uuid4().hex
        self.started = time.monotonic()

    def record(self, stage, started, **values):
        self.runtime.emit("voice_metrics", {
            "turn_id": self.id, "stage": stage,
            "duration_ms": round(max(0, time.monotonic() - started) * 1000, 1),
            **values,
        })

    @contextmanager
    def activate(self):
        token = _current.set(self)
        try:
            yield self
        finally:
            _current.reset(token)

def current_trace():
    return _current.get()
