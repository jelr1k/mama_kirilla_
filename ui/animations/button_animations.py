from __future__ import annotations

import logging
from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QPropertyAnimation,
    QRectF,
    Property,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import (
    QPushButton,
    QWidget,
)

logger = logging.getLogger("jarvis.ui.animations.buttons")


class ButtonHoverFilter(QObject):
    """Анимация плавного свечения при наведении (hover glow) и тактильного клика для кнопок."""

    def __init__(self, target_button: QPushButton):
        self.button = target_button
        self._glow = 0.0
        self._anim: QPropertyAnimation | None = None
        super().__init__(target_button)

    def get_glow(self) -> float:
        return self._glow

    def set_glow(self, val: float) -> None:
        self._glow = val
        if hasattr(self, "button") and self.button:
            self.button.update()

    glow = Property(float, get_glow, set_glow)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if not hasattr(self, "button") or obj is not self.button:
            return super().eventFilter(obj, event)

        etype = event.type()
        if etype == QEvent.Type.Enter:
            self._start_glow_anim(1.0)
        elif etype == QEvent.Type.Leave:
            self._start_glow_anim(0.0)
        elif etype == QEvent.Type.MouseButtonPress:
            self.button.move(self.button.x(), self.button.y() + 1)
        elif etype == QEvent.Type.MouseButtonRelease:
            self.button.move(self.button.x(), self.button.y() - 1)
        elif etype == QEvent.Type.Paint:
            # Даем выполниться стандартной отрисовке
            self.button.removeEventFilter(self)
            self.button.event(event)
            self.button.installEventFilter(self)

            # Поверх плавно рисуем неоновое свечение пропорционально glow
            if self._glow > 0.01:
                p = QPainter(self.button)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                r = QRectF(self.button.rect()).adjusted(1, 1, -1, -1)

                border_alpha = int(180 * self._glow)
                p.setPen(QPen(QColor(0, 229, 255, border_alpha), 1.2))
                fill_alpha = int(22 * self._glow)
                p.setBrush(QBrush(QColor(0, 229, 255, fill_alpha)))
                p.drawRoundedRect(r, 6.0, 6.0)
                p.end()
            return True
        return super().eventFilter(obj, event)

    def _start_glow_anim(self, target: float) -> None:
        if self._anim:
            self._anim.stop()
        anim = QPropertyAnimation(self, b"glow", self)
        anim.setDuration(140)
        anim.setStartValue(self._glow)
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim = anim
        anim.start()


def install_button_micro_interactions(parent: QWidget) -> None:
    """Устанавливает плавную анимацию наведения и тактильный отклик на все QPushButton внутри контейнера."""
    for btn in parent.findChildren(QPushButton):
        existing = [c for c in btn.children() if isinstance(c, ButtonHoverFilter)]
        if not existing:
            filt = ButtonHoverFilter(btn)
            btn.installEventFilter(filt)
