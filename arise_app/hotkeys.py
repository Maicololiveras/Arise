"""Windows hotkeys on a dedicated message-loop thread."""
import ctypes
import os
import threading
from ctypes import wintypes

class Hotkeys:
    def __init__(self, wake, stop):
        self.wake, self.stop = wake, stop
        self.thread_id = None
        self.thread = None
        self.ready = threading.Event()
        self.registered = False

    def start(self):
        if os.name != "nt":
            return False
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        self.ready.wait(2)
        return self.registered

    def _run(self):
        user = ctypes.windll.user32
        self.thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        msg = wintypes.MSG()
        user.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)  # create queue
        # MOD_CONTROL | MOD_ALT | MOD_NOREPEAT
        wake = bool(user.RegisterHotKey(None, 1, 0x4003, 0x41))
        stop = bool(user.RegisterHotKey(None, 2, 0x4003, 0x1B))
        self.registered = wake and stop
        self.ready.set()
        try:
            while user.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == 0x0312:
                    if msg.wParam == 1:
                        self.wake()
                    elif msg.wParam == 2:
                        self.stop()
        finally:
            user.UnregisterHotKey(None, 1)
            user.UnregisterHotKey(None, 2)

    def close(self):
        if self.thread_id:
            ctypes.windll.user32.PostThreadMessageW(self.thread_id, 0x0012, 0, 0)
            self.thread.join(timeout=2)
