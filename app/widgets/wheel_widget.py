import math
import random
from typing import List, Optional

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    Qt,
    Property,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPolygonF, QFontMetrics
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QWidget

from ..models import Theme


class WheelWidget(QWidget):
    landed = Signal(int)  # theme_id
    clicked = Signal()

    def __init__(self, themes: List[Theme], parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.themes = themes
        self._angle = 0.0
        self._target_index: Optional[int] = None
        self._animation = QPropertyAnimation(self, b"angle")
        self._animation.finished.connect(self._on_finished)
        self.setMinimumSize(320, 320)

    def getAngle(self) -> float:
        return self._angle

    def setAngle(self, value: float):
        self._angle = value
        self.update()

    angle = Property(float, getAngle, setAngle)

    def is_spinning(self) -> bool:
        return self._animation.state() == QPropertyAnimation.Running

    def spin_to(self, target_index: int, duration_ms: int = 3000):
        if self.is_spinning():
            return
        n = len(self.themes)
        seg = 360.0 / n
        wedge_center = target_index * seg + seg / 2
        final_mod = (360.0 - wedge_center) % 360.0
        current_mod = self._angle % 360.0
        full_spins = 5 * 360.0
        delta = (final_mod - current_mod) % 360.0
        target_angle = self._angle + full_spins + delta
        self._target_index = target_index
        self._animation.stop()
        self._animation.setDuration(duration_ms)
        self._animation.setStartValue(self._angle)
        self._animation.setEndValue(target_angle)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self._animation.start()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def _on_finished(self):
        if self._target_index is not None:
            theme = self.themes[self._target_index]
            self.landed.emit(theme.id)
            self._target_index = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        side = min(self.width(), self.height()) - 20
        rect = QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)
        center = rect.center()

        n = len(self.themes)
        seg = 360.0 / n

        painter.save()
        painter.translate(center)
        painter.rotate(self._angle)
        painter.translate(-center.x(), -center.y())

        font = QFont(self.font())
        font.setBold(True)
        font.setPointSize(max(8, side // 28))
        painter.setFont(font)

        for i, theme in enumerate(self.themes):
            start_angle = 90 - i * seg
            span_angle = -seg
            path = QPainterPath()
            path.moveTo(center)
            path.arcTo(rect, start_angle, span_angle)
            path.closeSubpath()
            painter.setBrush(QColor(theme.color))
            painter.setPen(QPen(QColor("#1a1a1a"), 2))
            painter.drawPath(path)

            mid_angle_deg = start_angle + span_angle / 2
            label_radius = side * 0.33
            rad = math.radians(mid_angle_deg)
            label_pos = QPointF(
                center.x() + label_radius * math.cos(rad),
                center.y() - label_radius * math.sin(rad),
            )
            painter.save()
            painter.translate(label_pos)
            text_angle = -mid_angle_deg
            if 90 < (mid_angle_deg % 360) < 270:
                text_angle += 180
            painter.rotate(text_angle)
            painter.setPen(QColor("#ffffff"))
            fm = QFontMetrics(font)
            elided = fm.elidedText(theme.name, Qt.ElideRight, int(side * 0.42))
            painter.drawText(QRectF(-side * 0.22, -12, side * 0.44, 24), Qt.AlignCenter, elided)
            painter.restore()

        painter.restore()

        painter.setBrush(QColor("#222222"))
        painter.setPen(QPen(QColor("#000000"), 2))
        painter.drawEllipse(center, side * 0.045, side * 0.045)

        pointer = QPolygonF(
            [
                QPointF(center.x() - side * 0.035, rect.top() - 6),
                QPointF(center.x() + side * 0.035, rect.top() - 6),
                QPointF(center.x(), rect.top() + side * 0.045),
            ]
        )
        painter.setBrush(QColor("#f1c40f"))
        painter.setPen(QPen(QColor("#000000"), 1.5))
        painter.drawPolygon(pointer)

        painter.end()

    @staticmethod
    def random_index(n: int) -> int:
        return random.randrange(n)
