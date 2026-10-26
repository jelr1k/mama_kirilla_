from __future__ import annotations

import logging
from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QTimer,
    Qt,
)
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QGroupBox,
    QProgressBar,
    QWidget,
)

logger = logging.getLogger("jarvis.ui.animations.effects")


class PulsingEffect:
    """Эффект мягкой цикличной пульсации прозрачности для акцентных элементов."""

    def __init__(
        self,
        target_widget: QWidget,
        min_opacity: float = 0.35,
        max_opacity: float = 1.0,
        period_ms: int = 1200,
    ):
        self.widget = target_widget
        self.min_opacity = min_opacity
        self.max_opacity = max_opacity
        self.period_ms = period_ms
        self.effect: QGraphicsOpacityEffect | None = None
        self.anim: QPropertyAnimation | None = None

    def start(self) -> None:
        if self.anim and self.anim.state() == QPropertyAnimation.State.Running:
            return
        if not self.effect:
            self.effect = QGraphicsOpacityEffect(self.widget)
            self.widget.setGraphicsEffect(self.effect)

        anim = QPropertyAnimation(self.effect, b"opacity", self.widget)
        anim.setDuration(self.period_ms // 2)
        anim.setStartValue(self.max_opacity)
        anim.setKeyValueAt(0.5, self.min_opacity)
        anim.setEndValue(self.max_opacity)
        anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        anim.setLoopCount(-1)
        self.anim = anim
        anim.start()

    def stop(self) -> None:
        if self.anim:
            self.anim.stop()
            self.anim = None
        if self.effect:
            self.effect.setOpacity(1.0)
            self.widget.setGraphicsEffect(None)
            self.effect = None


class SmoothScroller:
    """Плавный скролл к концу контейнера/текста."""

    def __init__(self, scroll_bar, duration_ms: int = 140):
        self.scroll_bar = scroll_bar
        self.duration_ms = duration_ms
        self._anim: QPropertyAnimation | None = None

    def scroll_to_bottom(self) -> None:
        target = self.scroll_bar.maximum()
        current = self.scroll_bar.value()
        if abs(target - current) < 4:
            self.scroll_bar.setValue(target)
            return

        if self._anim and self._anim.state() == QPropertyAnimation.State.Running:
            self._anim.stop()

        anim = QPropertyAnimation(self.scroll_bar, b"value", self.scroll_bar)
        anim.setDuration(self.duration_ms)
        anim.setStartValue(current)
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._anim = anim
        anim.start()


class ThinkingIndicator(QProgressBar):
    """Стильный неоновый анимированный индикатор раздумий и генерации."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setRange(0, 0)  # Режим marquee / бегущей полосы
        self.setFixedHeight(3)
        self.setTextVisible(False)
        self.setStyleSheet(
            """
            QProgressBar {
                background-color: transparent;
                border: none;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0077aa, stop:0.5 #00e5ff, stop:1 #10b981);
                border-radius: 1px;
            }
            """
        )
        self.hide()

    def start(self) -> None:
        self.show()

    def stop(self) -> None:
        self.hide()


def fade_in_window(window: QWidget, duration_ms: int = 240) -> QPropertyAnimation:
    """Плавное появление окна или диалога."""
    anim = QPropertyAnimation(window, b"windowOpacity", window)
    anim.setDuration(duration_ms)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.start()
    return anim


def animate_cards_entrance(container: QWidget, delay_step_ms: int = 40) -> list[QPropertyAnimation]:
    """Каскадная анимация плавного появления блоков (QGroupBox) при входе на страницу."""
    boxes = container.findChildren(QGroupBox)
    animations = []
    for i, box in enumerate(boxes):
        effect = QGraphicsOpacityEffect(box)
        box.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", box)
        anim.setDuration(180)
        anim.setStartValue(0.1)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutQuad)

        delay = i * delay_step_ms
        if delay == 0:
            anim.start()
        else:
            QTimer.singleShot(delay, anim.start)
        animations.append(anim)
    return animations
