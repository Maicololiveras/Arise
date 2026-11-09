"""End a captured turn by elapsed PCM duration, independent of output speech."""
from collections import deque
import numpy as np

class TurnDetector:
    def __init__(self, silence_ms=1400, threshold=300):
        self.silence_ms=silence_ms;self.threshold=threshold;self.reset()
    def reset(self):
        self.chunks=[];self.preroll=deque(maxlen=10);self.voiced_ms=0;self.quiet_ms=0;self.total_ms=0;self.started=False
    def feed(self,pcm,threshold=None):
        ms=len(pcm)/32  # mono PCM16 at 16 kHz
        amplitude=np.abs(np.frombuffer(pcm,dtype='<i2').astype(np.float32)).mean() if pcm else 0
        began=False
        if amplitude>(threshold if threshold is not None else self.threshold):
            self.voiced_ms+=ms;self.quiet_ms=0
            if not self.started and self.voiced_ms>=80:
                self.started=True;began=True;self.chunks=list(self.preroll)
        elif self.started:self.quiet_ms+=ms
        else:self.voiced_ms=0
        if self.started:self.chunks.append(pcm);self.total_ms+=ms
        else:self.preroll.append(pcm)
        if self.started and (self.quiet_ms>=self.silence_ms or self.total_ms>=30000):
            result=b''.join(self.chunks);self.reset();return began,result
        return began,None
