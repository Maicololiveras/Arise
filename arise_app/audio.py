"""Bounded native PCM capture/playback. No microphone opened by construction."""
import queue
import threading
from collections import deque
import numpy as np


def resample(pcm, source, target):
    if source == target:
        return pcm
    data = np.frombuffer(pcm, dtype="<i2")
    if not len(data):
        return b""
    count = round(len(data) * target / source)
    return np.interp(np.arange(count) * source / target, np.arange(len(data)), data).astype("<i2").tobytes()


class Audio:
    def __init__(self, input_device=None, output_device=None):
        self.input_device, self.output_device = input_device, output_device
        self.incoming = queue.Queue(maxsize=150)  # 3 seconds; never accumulate idle audio
        self.buffers = deque()
        self.lock = threading.RLock()
        self.capture = self.playback = None
        self.played = 0
        self.item_id = None
        self.output_rate = 24000
        self.speaking = False
        self.dropped = 0
        self.muted = False

    @staticmethod
    def devices():
        import sounddevice as sd
        return [{"id": i, "name": d["name"], "input": d["max_input_channels"] > 0,
            "output": d["max_output_channels"] > 0} for i, d in enumerate(sd.query_devices())]

    def open(self):
        import sounddevice as sd
        if self.capture:
            return
        self.capture = sd.RawInputStream(device=self.input_device, samplerate=16000, channels=1,
            dtype="int16", blocksize=320, callback=self._capture)
        try:
            self.playback = sd.RawOutputStream(device=self.output_device, samplerate=self.output_rate,
                channels=1, dtype="int16", blocksize=480, callback=self._playback)
            self.playback.start()
            self.capture.start()
        except Exception:
            self.close()
            raise

    def _capture(self, data, frames, timing, status):
        if self.muted:
            return
        try:
            self.incoming.put_nowait(bytes(data))
        except queue.Full:
            self.dropped += 1
            try:
                self.incoming.get_nowait()
                self.incoming.put_nowait(bytes(data))
            except (queue.Empty, queue.Full):
                pass

    def read(self, timeout=.1):
        try:
            return self.incoming.get(timeout=timeout)
        except queue.Empty:
            return None

    def clear_input(self):
        while True:
            try:
                self.incoming.get_nowait()
            except queue.Empty:
                return

    def play(self, pcm, rate=24000, item_id=None):
        pcm = resample(pcm, rate, self.output_rate)
        with self.lock:
            if item_id and item_id != self.item_id:
                self.played, self.item_id = 0, item_id
            if sum(len(part) for part in self.buffers) + len(pcm) > 24000 * 2 * 30:
                raise RuntimeError("La salida de audio supera el límite de 30 segundos.")
            self.buffers.append(pcm)
            self.speaking = True

    def _playback(self, out, frames, timing, status):
        needed = frames * 2
        result = bytearray()
        with self.lock:
            while self.buffers and len(result) < needed:
                chunk = self.buffers.popleft()
                take = min(len(chunk), needed - len(result))
                result.extend(chunk[:take])
                if take < len(chunk):
                    self.buffers.appendleft(chunk[take:])
            self.played += len(result) // 2
            self.speaking = bool(self.buffers)
        out[:] = bytes(result) + b"\0" * (needed - len(result))

    def interrupt(self):
        with self.lock:
            result = {"item_id": self.item_id, "audio_end_ms": self.played * 1000 // self.output_rate}
            self.buffers.clear()
            self.speaking = False
            self.item_id = None
            self.played = 0
            return result

    def close(self):
        self.interrupt()
        for name in ("capture", "playback"):
            stream = getattr(self, name)
            setattr(self, name, None)
            if stream:
                try:
                    stream.stop()
                finally:
                    stream.close()
        self.clear_input()
