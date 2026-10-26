from __future__ import annotations

import logging
from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    QRectF,
    Qt,
    Property,
    Signal,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QTabBar,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger("jarvis.ui.animations.tabs")


class SlidingStackedWidget(QStackedWidget):
    """Стек виджетов с плавной кинематической анимацией скольжения и фейда."""

    animation_finished = Signal()

    def __init__(self, parent: QWidget | None = None, duration_ms: int = 220):
        super().__init__(parent)
        self.duration_ms = duration_ms
        self._anim_group: QParallelAnimationGroup | None = None
        self._is_animating = False

    def _reset_all_widgets_state(self, active_idx: int) -> None:
        """Централизованно сбрасывает позиции, геометрию, видимость и графические эффекты всех вкладок."""
        if self._anim_group:
            self._anim_group.stop()
            self._anim_group = None
        self._is_animating = False

        target_rect = self.rect()
        for i in range(self.count()):
            w = self.widget(i)
            if not w:
                continue
            w.setGraphicsEffect(None)
            w.move(0, 0)
            w.setGeometry(target_rect)
            if i == active_idx:
                w.show()
                w.raise_()
            else:
                w.hide()
        self.setCurrentIndex(active_idx)

    def slide_to_index(self, next_idx: int) -> None:
        if next_idx < 0 or next_idx >= self.count():
            return

        old_idx = self.currentIndex()
        if old_idx == next_idx:
            return

        # При быстром переключении гарантированно сбрасываем состояние всех виджетов
        if self._is_animating:
            self._reset_all_widgets_state(old_idx)

        old_widget = self.widget(old_idx)
        next_widget = self.widget(next_idx)

        w = self.frameRect().width()
        h = self.frameRect().height()

        if w <= 1 or h <= 1 or not self.isVisible():
            self._reset_all_widgets_state(next_idx)
            self.animation_finished.emit()
            return

        direction = 1 if next_idx > old_idx else -1

        next_widget.setGeometry(direction * w, 0, w, h)
        next_widget.show()
        next_widget.raise_()

        self._is_animating = True

        anim_old_pos = QPropertyAnimation(old_widget, b"pos", self)
        anim_old_pos.setDuration(self.duration_ms)
        anim_old_pos.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim_old_pos.setStartValue(QPoint(0, 0))
        anim_old_pos.setEndValue(QPoint(-direction * w, 0))

        anim_new_pos = QPropertyAnimation(next_widget, b"pos", self)
        anim_new_pos.setDuration(self.duration_ms)
        anim_new_pos.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim_new_pos.setStartValue(QPoint(direction * w, 0))
        anim_new_pos.setEndValue(QPoint(0, 0))

        effect_old = QGraphicsOpacityEffect(old_widget)
        old_widget.setGraphicsEffect(effect_old)
        anim_old_fade = QPropertyAnimation(effect_old, b"opacity", self)
        anim_old_fade.setDuration(int(self.duration_ms * 0.8))
        anim_old_fade.setStartValue(1.0)
        anim_old_fade.setEndValue(0.15)

        effect_new = QGraphicsOpacityEffect(next_widget)
        next_widget.setGraphicsEffect(effect_new)
        anim_new_fade = QPropertyAnimation(effect_new, b"opacity", self)
        anim_new_fade.setDuration(self.duration_ms)
        anim_new_fade.setStartValue(0.2)
        anim_new_fade.setEndValue(1.0)

        group = QParallelAnimationGroup(self)
        group.addAnimation(anim_old_pos)
        group.addAnimation(anim_new_pos)
        group.addAnimation(anim_old_fade)
        group.addAnimation(anim_new_fade)

        def _on_finished():
            self._reset_all_widgets_state(next_idx)
            self.animation_finished.emit()

        group.finished.connect(_on_finished)
        self._anim_group = group
        group.start()


class AnimatedTabBar(QTabBar):
    """Таб-бар с плавной анимацией наведения (hover glow) и скользящей полосой активной вкладки."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setDrawBase(False)
        self._indicator_x = 0.0
        self._indicator_w = 0.0
        self._hover_index = -1
        self._hover_glow = 0.0
        self._anim_ind_x: QPropertyAnimation | None = None
        self._anim_ind_w: QPropertyAnimation | None = None
        self._anim_hover: QPropertyAnimation | None = None
        self.currentChanged.connect(self._on_current_changed)

    def get_ind_x(self) -> float:
        return self._indicator_x

    def set_ind_x(self, val: float) -> None:
        self._indicator_x = val
        self.update()

    ind_x = Property(float, get_ind_x, set_ind_x)

    def get_ind_w(self) -> float:
        return self._indicator_w

    def set_ind_w(self, val: float) -> None:
        self._indicator_w = val
        self.update()

    ind_w = Property(float, get_ind_w, set_ind_w)

    def get_hover_glow(self) -> float:
        return self._hover_glow

    def set_hover_glow(self, val: float) -> None:
        self._hover_glow = val
        self.update()

    hover_glow = Property(float, get_hover_glow, set_hover_glow)

    def _on_current_changed(self, idx: int) -> None:
        rect = self.tabRect(idx)
        if rect.isValid():
            self._animate_indicator(float(rect.x()), float(rect.width()))

    def _animate_indicator(self, target_x: float, target_w: float) -> None:
        if self._anim_ind_x:
            self._anim_ind_x.stop()
        if self._anim_ind_w:
            self._anim_ind_w.stop()

        ax = QPropertyAnimation(self, b"ind_x", self)
        ax.setDuration(180)
        ax.setStartValue(self._indicator_x or target_x)
        ax.setEndValue(target_x)
        ax.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim_ind_x = ax
        ax.start()

        aw = QPropertyAnimation(self, b"ind_w", self)
        aw.setDuration(180)
        aw.setStartValue(self._indicator_w or target_w)
        aw.setEndValue(target_w)
        aw.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim_ind_w = aw
        aw.start()

    def mouseMoveEvent(self, event) -> None:
        super().mouseMoveEvent(event)
        idx = self.tabAt(event.position().toPoint())
        if idx != self._hover_index:
            self._hover_index = idx
            self._animate_hover(1.0 if (idx >= 0 and idx != self.currentIndex()) else 0.0)

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._hover_index = -1
        self._animate_hover(0.0)

    def _animate_hover(self, target: float) -> None:
        if self._anim_hover:
            self._anim_hover.stop()
        ah = QPropertyAnimation(self, b"hover_glow", self)
        ah.setDuration(140)
        ah.setStartValue(self._hover_glow)
        ah.setEndValue(target)
        ah.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim_hover = ah
        ah.start()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Плавная подсветка вкладки при наведении курсора
        if self._hover_glow > 0.01 and self._hover_index >= 0 and self._hover_index != self.currentIndex():
            hr = self.tabRect(self._hover_index)
            if hr.isValid():
                alpha = int(45 * self._hover_glow)
                p.setPen(QPen(QColor(0, 229, 255, int(130 * self._hover_glow)), 1.0))
                p.setBrush(QBrush(QColor(0, 229, 255, alpha)))
                p.drawRoundedRect(QRectF(hr).adjusted(2, 2, -2, -1), 5.0, 5.0)

        # Скользящая неоновая полоса активной вкладки
        if self._indicator_w > 0:
            h = self.height()
            line_rect = QRectF(self._indicator_x + 4, h - 3, self._indicator_w - 8, 3)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor("#00e5ff")))
            p.drawRoundedRect(line_rect, 1.5, 1.5)
        p.end()


class AnimatedTabWidget(QWidget):
    """Виджет вкладок со скользящими страницами и анимированным таб-баром."""

    currentChanged = Signal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tab_bar = AnimatedTabBar(self)
        self.tab_bar.currentChanged.connect(self._on_bar_changed)

        self.pane = QFrame(self)
        self.pane.setObjectName("animatedTabPane")
        self.pane.setStyleSheet(
            "#animatedTabPane { border: 1px solid #1a2336; border-radius: 8px; background-color: #0f1728; padding: 6px; }"
        )
        pane_layout = QVBoxLayout(self.pane)
        pane_layout.setContentsMargins(4, 4, 4, 4)
        pane_layout.setSpacing(0)

        self.stack = SlidingStackedWidget(self.pane)
        pane_layout.addWidget(self.stack)

        layout.addWidget(self.tab_bar)
        layout.addWidget(self.pane)

    def addTab(self, widget: QWidget, label: str) -> int:
        idx = self.stack.addWidget(widget)
        self.tab_bar.addTab(label)
        return idx

    def count(self) -> int:
        return self.tab_bar.count()

    def currentIndex(self) -> int:
        return self.tab_bar.currentIndex()

    def currentWidget(self) -> QWidget | None:
        return self.stack.currentWidget()

    def widget(self, index: int) -> QWidget | None:
        return self.stack.widget(index)

    def setCurrentIndex(self, index: int) -> None:
        if 0 <= index < self.count():
            self.tab_bar.setCurrentIndex(index)

    def setCurrentWidget(self, widget: QWidget) -> None:
        idx = self.stack.indexOf(widget)
        if idx >= 0:
            self.setCurrentIndex(idx)

    def _on_bar_changed(self, index: int) -> None:
        self.stack.slide_to_index(index)
        self.currentChanged.emit(index)
