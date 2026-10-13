"""Shared application identity from the actual animated ARISE orb."""
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage
import assets


def icon_image(size):
    atlas = QImage(str(Path(assets.__file__).parent / 'orb-atlas.png'))
    if atlas.isNull() or atlas.width() != atlas.height() * 24:
        raise RuntimeError('No se pudo cargar el atlas del orbe ARISE.')
    # The first animation frame is the static identity, including its halo and
    # particles. Crop before resizing so adjacent frames never enter the icon.
    orb = atlas.copy(0, 0, atlas.height(), atlas.height())
    return orb.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
