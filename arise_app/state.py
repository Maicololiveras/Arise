"""State exposed to the orb; activity and privacy remain separate."""
from dataclasses import dataclass, asdict
import threading

STATES = {"idle", "wake_detected", "connecting", "listening", "understanding", "working", "waiting_approval", "speaking", "offline", "error", "privacy_blocked"}
LABELS = {"idle": "OYE ARISE", "wake_detected": "AQUÍ ESTOY", "connecting": "CONECTANDO", "listening": "TE ESCUCHO", "understanding": "PROCESANDO", "working": "TRABAJANDO", "waiting_approval": "TU DECISIÓN", "speaking": "ARISE", "offline": "SIN CONEXIÓN", "error": "REVISAR AVISO", "privacy_blocked": "SILENCIADO"}

@dataclass
class OrbState:
    state: str = "idle"
    activity: str = "OYE ARISE"
    microphone: bool = False
    screen: bool = False
    control: bool = False
    speaker: str = "orchestrator"
    task: str | None = None

class StateBus:
    def __init__(self, emit):
        self.value = OrbState()
        self.emit = emit
        self.lock = threading.RLock()

    def update(self, state=None, **changes):
        with self.lock:
            if state is not None:
                if state not in STATES:
                    raise ValueError("Estado desconocido")
                self.value.state = state
                self.value.activity = LABELS[state]
            for key, value in changes.items():
                if key not in OrbState.__dataclass_fields__:
                    raise ValueError("Campo desconocido")
                setattr(self.value, key, value)
            snapshot = asdict(self.value)
        self.emit("orb", snapshot)
        return snapshot
