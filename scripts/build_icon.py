"""Package the real animated ARISE orb as a multi-resolution Windows icon."""
from pathlib import Path
import os
import struct
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtWidgets import QApplication
from arise_app.brand import icon_image


def build(destination):
    app=QApplication.instance() or QApplication([])
    images=[]
    for size in (16,24,32,48,64,128,256):
        canvas=icon_image(size)
        buffer=QBuffer();buffer.open(QIODevice.WriteOnly)
        if not canvas.save(buffer,'PNG'): raise RuntimeError('Could not render icon')
        images.append((size,bytes(buffer.data())))
    offset=6+16*len(images)
    entries=[]
    for size,data in images:
        entries.append(struct.pack('<BBBBHHII',size%256,size%256,0,0,1,32,len(data),offset))
        offset+=len(data)
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_bytes(struct.pack('<HHH',0,1,len(images))+b''.join(entries)+b''.join(data for _,data in images))

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='artifacts/arise.ico')
    build(parser.parse_args().output)
