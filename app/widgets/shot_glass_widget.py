from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, Qt, Property, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class ShotGlassWidget(QWidget):
    """A little glass that empties itself when a wrong answer is given."""

    finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._level = 1.0  # 1.0 = full, 0.0 = empty
        self._tilt = 0.0
        self.setMinimumSize(160, 200)
        self._level_anim = QPropertyAnimation(self, b"level")
        self._level_anim.setDuration(1100)
        self._level_anim.setStartValue(1.0)
        self._level_anim.setEndValue(0.0)
        self._level_anim.setEasingCurve(QEasingCurve.InQuad)
        self._tilt_anim = QPropertyAnimation(self, b"tilt")
        self._tilt_anim.setDuration(1100)
        self._tilt_anim.setKeyValueAt(0.0, 0.0)
        self._tilt_anim.setKeyValueAt(0.5, 35.0)
        self._tilt_anim.setKeyValueAt(1.0, 0.0)
        self._level_anim.finished.connect(self.finished.emit)

    def getLevel(self) -> float:
        return self._level

    def setLevel(self, value: float):
        self._level = value
        self.update()

    level = Property(float, getLevel, setLevel)

    def getTilt(self) -> float:
        return self._tilt

    def setTilt(self, value: float):
        self._tilt = value
        self.update()

    tilt = Property(float, getTilt, setTilt)

    def play(self):
        self._level = 1.0
        self._tilt = 0.0
        self._level_anim.stop()
        self._tilt_anim.stop()
        self._level_anim.start()
        self._tilt_anim.start()

    def reset(self):
        self._level_anim.stop()
        self._tilt_anim.stop()
        self._level = 1.0
        self._tilt = 0.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        glass_w = min(w * 0.5, 90)
        glass_h = min(h * 0.75, 140)
        top_left_x = (w - glass_w) / 2
        top_y = (h - glass_h) / 2

        painter.translate(w / 2, top_y + glass_h / 2)
        painter.rotate(self._tilt)
        painter.translate(-w / 2, -(top_y + glass_h / 2))

        top_w = glass_w
        bottom_w = glass_w * 0.7
        glass_path = QPainterPath()
        glass_path.moveTo(top_left_x, top_y)
        glass_path.lineTo(top_left_x + top_w, top_y)
        glass_path.lineTo(top_left_x + top_w - (top_w - bottom_w) / 2, top_y + glass_h)
        glass_path.lineTo(top_left_x + (top_w - bottom_w) / 2, top_y + glass_h)
        glass_path.closeSubpath()

        if self._level > 0.001:
            liquid_top_y = top_y + glass_h * (1 - self._level)
            frac_from_top = (liquid_top_y - top_y) / glass_h
            liquid_half_top_w = (top_w - (top_w - bottom_w) * frac_from_top) / 2
            liquid_half_bottom_w = bottom_w / 2
            cx = top_left_x + top_w / 2
            liquid_path = QPainterPath()
            liquid_path.moveTo(cx - liquid_half_top_w, liquid_top_y)
            liquid_path.lineTo(cx + liquid_half_top_w, liquid_top_y)
            liquid_path.lineTo(cx + liquid_half_bottom_w, top_y + glass_h)
            liquid_path.lineTo(cx - liquid_half_bottom_w, top_y + glass_h)
            liquid_path.closeSubpath()

            gradient = QLinearGradient(0, top_y, 0, top_y + glass_h)
            gradient.setColorAt(0, QColor("#ffe07a"))
            gradient.setColorAt(1, QColor("#e8a33d"))
            painter.setBrush(gradient)
            painter.setPen(Qt.NoPen)
            painter.drawPath(liquid_path)

        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#d7e3f4"), 3))
        painter.drawPath(glass_path)

        painter.end()
