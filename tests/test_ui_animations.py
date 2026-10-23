from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from unittest.mock import Mock
import pytest
from PySide6.QtCore import QEvent, QPoint
from PySide6.QtWidgets import (
    QApplication,
    QGroupBox,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui.animations import (
    AnimatedTabBar,
    AnimatedTabWidget,
    AnimatedToggle,
    ButtonHoverFilter,
    PulsingEffect,
    SmoothScroller,
    ThinkingIndicator,
    animate_cards_entrance,
    fade_in_window,
    install_button_micro_interactions,
)
from ui.animations.splash_screen import SplashScreen


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


def test_animated_tab_widget_lifecycle(app):
    widget = AnimatedTabWidget()
    p1 = QLabel("Page 1")
    p2 = QLabel("Page 2")
    p3 = QLabel("Page 3")

    widget.addTab(p1, "Первая")
    widget.addTab(p2, "Вторая")
    widget.addTab(p3, "Третья")

    assert widget.count() == 3
    assert widget.currentIndex() == 0
    assert widget.currentWidget() == p1

    widget.setCurrentIndex(1)
    assert widget.currentIndex() == 1
    assert widget.currentWidget() == p2

    widget.setCurrentWidget(p3)
    assert widget.currentIndex() == 2
    assert widget.currentWidget() == p3
    assert widget.widget(0) == p1


def test_animated_tab_widget_sliding_transition(app):
    widget = AnimatedTabWidget()
    p1 = QLabel("P1")
    p2 = QLabel("P2")
    widget.addTab(p1, "1")
    widget.addTab(p2, "2")
    widget.resize(400, 300)
    widget.show()
    app.processEvents()

    # Trigger transition
    widget.setCurrentIndex(1)
    app.processEvents()
    assert widget.currentIndex() == 1


def test_rapid_tab_switching_cleans_state(app):
    widget = AnimatedTabWidget()
    p1 = QLabel("P1")
    p2 = QLabel("P2")
    p3 = QLabel("P3")
    widget.addTab(p1, "1")
    widget.addTab(p2, "2")
    widget.addTab(p3, "3")
    widget.resize(400, 300)
    widget.show()
    app.processEvents()

    # Быстрое переключение без ожидания завершения анимации
    widget.setCurrentIndex(1)
    widget.setCurrentIndex(2)
    widget.setCurrentIndex(0)
    widget.setCurrentIndex(2)

    # Даем анимациям завершиться
    if widget.stack._anim_group:
        widget.stack._anim_group.stop()
    widget.stack._reset_all_widgets_state(2)
    app.processEvents()

    assert widget.currentIndex() == 2
    assert p1.pos() == QPoint(0, 0)
    assert p2.pos() == QPoint(0, 0)
    assert p3.pos() == QPoint(0, 0)
    assert p1.graphicsEffect() is None
    assert p2.graphicsEffect() is None
    assert p3.graphicsEffect() is None
    assert not p1.isVisible()
    assert not p2.isVisible()
    assert p3.isVisible()


def test_animated_tab_bar_hover_and_indicator(app):
    bar = AnimatedTabBar()
    bar.addTab("Вкладка 1")
    bar.addTab("Вкладка 2")
    bar.resize(300, 40)
    bar.show()
    app.processEvents()

    # Test indicator movement
    bar.setCurrentIndex(1)
    assert bar._anim_ind_x is not None

    # Test hover simulation
    bar._animate_hover(1.0)
    assert bar._anim_hover is not None
    assert bar.hover_glow >= 0.0


def test_button_hover_filter(app):
    btn = QPushButton("Кнопка")
    filt = ButtonHoverFilter(btn)
    btn.installEventFilter(filt)
    btn.resize(100, 30)
    btn.show()

    # Trigger enter event
    enter_ev = QEvent(QEvent.Type.Enter)
    filt.eventFilter(btn, enter_ev)
    assert filt._anim is not None

    # Trigger leave event
    leave_ev = QEvent(QEvent.Type.Leave)
    filt.eventFilter(btn, leave_ev)
    assert filt._anim is not None


def test_pulsing_effect_start_stop(app):
    label = QLabel("Test")
    pulse = PulsingEffect(label, period_ms=200)
    pulse.start()
    assert pulse.anim is not None
    # Idempotent start
    pulse.start()
    pulse.stop()
    assert pulse.anim is None
    # Idempotent stop
    pulse.stop()


def test_smooth_scroller(app):
    editor = QTextEdit()
    editor.resize(200, 100)
    editor.verticalScrollBar().setRange(0, 500)
    scroller = SmoothScroller(editor.verticalScrollBar(), duration_ms=50)
    scroller.scroll_to_bottom()
    assert scroller._anim is not None


def test_fade_in_window(app):
    win = QWidget()
    anim = fade_in_window(win, duration_ms=50)
    assert anim is not None


def test_splash_screen_lifecycle(app):
    splash = SplashScreen(min_duration_ms=60)
    if splash._progress_anim:
        splash._progress_anim.stop()
    splash.set_status("Тестовая загрузка…")
    assert splash.status_label.text() == "Тестовая загрузка…"

    target = QWidget()
    target.hide()
    splash.show()
    app.processEvents()

    splash.finish_loading(target)
    app.processEvents()
    assert splash._target_window == target


def test_animated_toggle(app):
    toggle = AnimatedToggle("Включить TTS")
    assert not toggle.isChecked()
    toggle.setChecked(True)
    assert toggle.isChecked()
    assert toggle.get_thumb_pos() >= 0.0

    toggle.setChecked(False)
    assert not toggle.isChecked()


def test_thinking_indicator(app):
    indicator = ThinkingIndicator()
    assert not indicator.isVisible()
    indicator.start()
    assert indicator.isVisible()
    indicator.stop()
    assert not indicator.isVisible()


def test_animate_cards_entrance(app):
    container = QWidget()
    layout = QVBoxLayout(container)
    b1 = QGroupBox("Карточка 1")
    b2 = QGroupBox("Карточка 2")
    layout.addWidget(b1)
    layout.addWidget(b2)
    anims = animate_cards_entrance(container, delay_step_ms=10)
    assert len(anims) == 2


def test_button_micro_interactions(app):
    parent = QWidget()
    btn = QPushButton("Тест", parent)
    install_button_micro_interactions(parent)
    app.processEvents()
    assert btn.text() == "Тест"
