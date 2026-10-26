from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QRectF,
    Qt,
    Property,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QWidget,
)


class AnimatedToggle(QCheckBox):
    """Плавный неоновый переключатель (свитч) с анимацией скольжения бегунка."""

    def __init__(self, text: str = "", parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._thumb_position = 1.0 if self.isChecked() else 0.0
        self._anim = QPropertyAnimation(self, b"thumb_position", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._on_toggled)

    def get_thumb_pos(self) -> float:
        return self._thumb_position

    def set_thumb_pos(self, pos: float) -> None:
        self._thumb_position = pos
        self.update()

    thumb_position = Property(float, get_thumb_pos, set_thumb_pos)

    def _on_toggled(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._thumb_position)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        track_w = 38.0
        track_h = 20.0
        track_y = (self.height() - track_h) / 2.0
        track_rect = QRectF(2.0, track_y, track_w, track_h)

        pos = self._thumb_position
        r = int(30 * (1 - pos) + 0 * pos)
        g = int(41 * (1 - pos) + 229 * pos)
        b = int(59 * (1 - pos) + 255 * pos)
        track_color = QColor(r, g, b)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(track_color))
        p.drawRoundedRect(track_rect, 10.0, 10.0)

        thumb_radius = 7.0
        thumb_x = 2.0 + 3.0 + pos * (track_w - 6.0 - 2 * thumb_radius) + thumb_radius
        thumb_y = track_y + 10.0

        p.setBrush(QBrush(QColor("#ffffff" if pos > 0.5 else "#94a3b8")))
        p.drawEllipse(QPoint(int(thumb_x), int(thumb_y)), thumb_radius, thumb_radius)

        if self.text():
            p.setPen(QPen(QColor("#e2e8f0")))
            p.drawText(int(track_w + 12), int(track_y + 14), self.text())
        p.end()
