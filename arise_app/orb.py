"""Low-overhead PNG-frame renderer, with native procedural renderer as fallback."""
import math
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, Signal, QPoint, QRectF
from PySide6.QtGui import QPainter, QColor, QPixmap, QRegion
from PySide6.QtWidgets import QWidget
import assets

class SpriteOrb(QWidget):
    size_changed = Signal(int)
    visibility_changed = Signal(bool)
    def __init__(self, size, x, y, frame_dir=None):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle("ARISE"); self.resize(size, size); self.move(x, y)
        folder = Path(frame_dir or Path(assets.__file__).parent / "frames")
        atlas = QPixmap(str(Path(assets.__file__).parent / "orb-atlas.png"))
        self.frames = [atlas.copy(i * (atlas.width() // 24), 0, atlas.width() // 24, atlas.height()) for i in range(24)] if not atlas.isNull() else [QPixmap(str(p)) for p in sorted(folder.glob("*.png"))]
        if not self.frames or any(f.isNull() for f in self.frames): raise RuntimeError("Fotogramas del orbe no disponibles")
        self.index = 0; self.status_label = "OYE ARISE"; self.state = "idle"; self.privacy = {}; self.drag = None; self.reduced = False
        self.size_changed.connect(self._resize); self.visibility_changed.connect(self.setVisible)
        self.timer = QTimer(self); self.timer.timeout.connect(self.tick); self.timer.start(100)
        self._resize(size)
    def tick(self):
        if not self.reduced and self.isVisible(): self.index = (self.index + 1) % len(self.frames); self.update()
    def _resize(self, value):
        self.resize(value, value); self.setMask(QRegion(self.rect(), QRegion.Ellipse)); self.update()
    def apply_state(self, payload):
        self.state = payload.get("state", self.state)
        self.status_label = payload.get("reason", self.status_label)
        self.privacy = payload.get("privacy", self.privacy)
        self.reduced = payload.get("reduced_motion", self.reduced)
        if payload.get("size"): self._resize(payload["size"])
        if "visible" in payload: self.setVisible(payload["visible"])
        self.update()
    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing); p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.drawPixmap(self.rect(), self.frames[self.index])
        colors = {"understanding": "#C792EA", "working": "#508EFF", "waiting_approval": "#FFC050", "error": "#FF646E", "speaking": "#FFAB66"}
        p.setPen(QColor(colors.get(self.state, "#74F6FF")))
        p.drawEllipse(self.rect().adjusted(4, 4, -4, -4))
        if self.privacy.get("microphone"):
            p.setBrush(QColor("#74F6FF")); p.drawEllipse(QRectF(self.width()*.45, self.height()*.83, 5, 5))
        if self.privacy.get("control"):
            p.setBrush(QColor("#FFC050")); p.drawEllipse(QRectF(self.width()*.57, self.height()*.83, 5, 5))
        p.end()
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton: self.drag = event.globalPosition().toPoint() - self.pos()
    def mouseMoveEvent(self, event):
        if self.drag is not None and event.buttons() & Qt.LeftButton: self.move(event.globalPosition().toPoint() - self.drag)
    def mouseReleaseEvent(self, event): self.drag = None


def build_orb(app, size, x, y, mode="sprite"):
    if mode == "sprite":
        try:
            window = SpriteOrb(size, x, y); window.show(); return app, window
        except RuntimeError: pass
    from assets.orb_original import build_app
    return build_app("", size, size, x, y, None, 0)
