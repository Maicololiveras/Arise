"""Export the user's native ARISE painter into a bounded 24-frame PNG loop."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import random
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from assets.orb_original import build_app
from PySide6.QtCore import QTimer
random.seed(42)
app, orb = build_app("", 192, 192, 0, 0, None, 0)
for timer in orb.findChildren(QTimer): timer.stop()
folder = Path(__file__).resolve().parents[1] / "assets/frames"
folder.mkdir(exist_ok=True)
orb.apply_state({"reason": "", "speaking": False, "listening": False})
# Hide redundant tiny status label: status belongs in the compact panel.
orb.status_label = ""
for i in range(24):
    orb.rotation = i * 6.28318530718 / 24
    orb.pulse = i * .2
    orb.ring_phase = i * 6.28318530718 / 24
    orb.update(); app.processEvents()
    orb.grab().save(str(folder / f"{i:03}.png"))
print(f"Exported {len(list(folder.glob('*.png')))} frames")
orb.hide()
