import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage, QPainter
app=QApplication([])
folder=Path(__file__).resolve().parents[1]/"assets"
frames=[QImage(str(p)) for p in sorted((folder/"frames").glob("*.png"))]
image=QImage(frames[0].width()*len(frames),frames[0].height(),QImage.Format_ARGB32);image.fill(0)
p=QPainter(image)
for index,frame in enumerate(frames):p.drawImage(index*frame.width(),0,frame)
p.end();image.save(str(folder/"orb-atlas.png"))
print('Atlas bytes:',(folder/'orb-atlas.png').stat().st_size)
