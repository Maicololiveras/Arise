import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from arise_app.assistant import Assistant
from arise_app.desktop import Controller,Settings
from arise_app.orb import build_orb
app=QApplication([]);app.setQuitOnLastWindowClosed(False)
with tempfile.TemporaryDirectory() as root:
 runtime=Assistant(root);app,orb=build_orb(app,96,10,10)
 controller=Controller(app,runtime,orb,start_voice=False)
 controller.panel.show();QTest.qWait(100)
 controller.panel.append('ARISE','Estoy listo. Conecta tu agente y elige tu voz en Ajustes.')
 controller.panel.grab().save('docs/panel.png');orb.grab().save('docs/orb.png')
 settings=Settings(controller);settings.show();QTest.qWait(100);settings.grab().save('docs/settings.png')
 controller.close();orb.removeEventFilter(controller);orb.close();settings.close();controller.panel.close();runtime.storage.db.close()
