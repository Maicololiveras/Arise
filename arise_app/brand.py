"""WEG identity from the official, user-supplied unmodified logo."""
from pathlib import Path
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QImage, QPainter, QColor
import assets


def icon_image(size):
    logo = QImage(str(Path(assets.__file__).parent / 'weg-logo.png'))
    if logo.isNull():
        raise RuntimeError('The official WEG logo is missing from this distribution.')
    canvas = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    canvas.fill(Qt.transparent)
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor('white'))
    painter.drawEllipse(QRectF(1, 1, size-2, size-2))
    fitted = logo.scaled(int(size*.74), int(size*.74), Qt.KeepAspectRatio, Qt.SmoothTransformation)
    painter.drawImage((size-fitted.width())//2, (size-fitted.height())//2, fitted)
    painter.end()
    return canvas
