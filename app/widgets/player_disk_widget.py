from typing import List

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from ..models import Player, Theme


class PlayerDiskWidget(QWidget):
    def __init__(self, themes: List[Theme], player: Player, parent=None):
        super().__init__(parent)
        self.themes = themes
        self.player = player
        self.setMinimumSize(64, 64)
        self.setMaximumSize(64, 64)

    def set_player(self, player: Player):
        self.player = player
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        side = min(self.width(), self.height()) - 6
        rect = QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)
        n = len(self.themes)
        seg = 360.0 / n

        for i, theme in enumerate(self.themes):
            start_angle = 90 - i * seg
            span_angle = -seg
            path = QPainterPath()
            path.moveTo(rect.center())
            path.arcTo(rect, start_angle, span_angle)
            path.closeSubpath()
            owned = theme.id in self.player.wedges
            painter.setBrush(QColor(theme.color) if owned else QColor("#3a3a3a"))
            painter.setPen(QPen(QColor("#111111"), 1.2))
            painter.drawPath(path)

        if self.player.awaiting_final:
            painter.setPen(QPen(QColor("#f1c40f"), 3))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(rect.adjusted(-2, -2, 2, 2))

        painter.end()
