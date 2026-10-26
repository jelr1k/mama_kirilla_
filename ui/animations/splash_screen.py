from __future__ import annotations

import logging
from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    Signal,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger("jarvis.ui.animations.splash")


class SplashScreen(QWidget):
    """Стильная заставка в стиле Discord / Cyberpunk при старте Kirieshka v2."""

    finished = Signal()

    def __init__(self, min_duration_ms: int = 1600):
        super().__init__()
        self.min_duration_ms = min_duration_ms
        self._fade_anim: QPropertyAnimation | None = None
        self._progress_anim: QPropertyAnimation | None = None
        self._ready_to_close = False
        self._target_window: QWidget | None = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.SplashScreen
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(480, 260)

        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.geometry()
            self.move(
                geo.x() + (geo.width() - self.width()) // 2,
                geo.y() + (geo.height() - self.height()) // 2,
            )

        self._build_ui()
        self._start_progress_animation()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)

        card = QFrame(self)
        card.setObjectName("splashCard")
        card.setStyleSheet(
            """
            #splashCard {
                background-color: #090d16;
                border: 1px solid #1e293b;
                border-radius: 14px;
            }
            """
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 24, 28, 24)
        card_layout.setSpacing(12)

        top_row = QHBoxLayout()
        title = QLabel("Kirieshka v2")
        title.setStyleSheet(
            "color: #00e5ff; font-size: 24px; font-weight: 700; font-family: 'Segoe UI', sans-serif;"
        )

        badge = QLabel("READY")
        badge.setStyleSheet(
            "color: #10b981; background: #064e3b; border: 1px solid #059669; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: 600;"
        )

        top_row.addWidget(title)
        top_row.addStretch()
        top_row.addWidget(badge)
        card_layout.addLayout(top_row)

        subtitle = QLabel("Локальный AI ассистент и рабочий контур")
        subtitle.setStyleSheet("color: #64748b; font-size: 12px;")
        card_layout.addWidget(subtitle)

        card_layout.addStretch()

        self.status_label = QLabel("Инициализация ядра системы…")
        self.status_label.setStyleSheet(
            "color: #cbd5e1; font-size: 12px; font-weight: 500;"
        )
        card_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                background-color: #162032;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0077aa, stop:1 #00e5ff);
                border-radius: 3px;
            }
            """
        )
        card_layout.addWidget(self.progress_bar)

        root_layout.addWidget(card)

    def _start_progress_animation(self) -> None:
        anim = QPropertyAnimation(self.progress_bar, b"value", self)
        anim.setDuration(self.min_duration_ms)
        anim.setStartValue(0)
        anim.setKeyValueAt(0.3, 35)
        anim.setKeyValueAt(0.65, 75)
        anim.setKeyValueAt(0.9, 92)
        anim.setEndValue(100)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        def _on_value_changed(val: int) -> None:
            if val < 30:
                self.status_label.setText("Инициализация ядра и EventBus…")
            elif val < 60:
                self.status_label.setText("Подключение контроллеров и тулов…")
            elif val < 85:
                self.status_label.setText("Проверка готовности Ollama и голоса…")
            else:
                self.status_label.setText("Запуск интерфейса…")

        anim.valueChanged.connect(_on_value_changed)
        anim.finished.connect(self._on_progress_finished)
        self._progress_anim = anim
        anim.start()

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)
        QApplication.processEvents()

    def _on_progress_finished(self) -> None:
        if self._ready_to_close:
            self._fade_out_and_finish()
        else:
            self._ready_to_close = True

    def finish_loading(self, target_window: QWidget | None = None) -> None:
        self._target_window = target_window
        if self._ready_to_close:
            self._fade_out_and_finish()
        else:
            self._ready_to_close = True

    def _fade_out_and_finish(self) -> None:
        if not self.isVisible():
            if self._target_window:
                self._target_window.show()
            self.finished.emit()
            self.close()
            return

        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(220)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        def _on_faded():
            if self._target_window:
                self._target_window.show()
            self.finished.emit()
            self.close()

        anim.finished.connect(_on_faded)
        self._fade_anim = anim
        anim.start()
