from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

HEALTH_URL = "http://127.0.0.1:8765/health"
TIMEOUT_SECS = 35


def _check_health() -> bool:
    try:
        req = urllib.request.Request(HEALTH_URL, headers={"User-Agent": "JarvisSplash/2.0"})
        with urllib.request.urlopen(req, timeout=0.6) as response:
            if response.status == 200:
                payload = json.loads(response.read().decode("utf-8"))
                if payload.get("status") == "ok":
                    return True
    except Exception:
        pass
    return False


def _cli_fallback() -> int:
    """Fallback if PySide6 is unavailable or in non-GUI environment."""
    t0 = time.time()
    while time.time() - t0 < TIMEOUT_SECS:
        if _check_health():
            return 0
        time.sleep(0.4)
    return 1


def run_gui_splash() -> int:
    try:
        from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
        from PySide6.QtGui import QColor
        from PySide6.QtWidgets import (
            QApplication,
            QFrame,
            QGraphicsDropShadowEffect,
            QHBoxLayout,
            QLabel,
            QProgressBar,
            QVBoxLayout,
            QWidget,
        )
    except Exception:
        return _cli_fallback()

    app = QApplication.instance() or QApplication(sys.argv)

    class DiscordSplashWindow(QWidget):
        def __init__(self):
            super().__init__()
            self.max_ticks = TIMEOUT_SECS * 5
            self.tick_count = 0
            self._fade_anim = None

            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.Tool
            )
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setFixedSize(440, 220)

            self._build_ui()
            self._center_window()

            self.timer = QTimer(self)
            self.timer.timeout.connect(self._on_tick)
            self.timer.start(200)

        def _center_window(self):
            screen = QApplication.primaryScreen()
            if screen:
                geo = screen.geometry()
                self.move(
                    geo.x() + (geo.width() - self.width()) // 2,
                    geo.y() + (geo.height() - self.height()) // 2,
                )

        def _build_ui(self):
            root = QVBoxLayout(self)
            root.setContentsMargins(14, 14, 14, 14)

            card = QFrame(self)
            card.setObjectName("splashCard")
            card.setStyleSheet("""
                #splashCard {
                    background-color: #0d1527;
                    border: 1px solid #1c2344;
                    border-radius: 14px;
                }
            """)

            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(30)
            shadow.setColor(QColor(0, 0, 0, 190))
            shadow.setOffset(0, 8)
            card.setGraphicsEffect(shadow)

            layout = QVBoxLayout(card)
            layout.setContentsMargins(24, 20, 24, 20)
            layout.setSpacing(12)

            # Top Header Row
            top_row = QHBoxLayout()
            top_row.setSpacing(10)

            orb = QLabel("⚡")
            orb.setStyleSheet("""
                background: color-mix(in srgb, #6ea8ff 15%, transparent);
                border: 1px solid color-mix(in srgb, #6ea8ff 35%, transparent);
                color: #6ea8ff;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                padding: 4px 8px;
            """)
            top_row.addWidget(orb)

            title_col = QVBoxLayout()
            title_col.setSpacing(2)
            title = QLabel("Kirieshcka v2")
            title.setStyleSheet("color: #ffffff; font-size: 17px; font-weight: 700; font-family: 'Segoe UI', sans-serif;")
            subtitle = QLabel("Локальный AI ассистент и рабочий контур")
            subtitle.setStyleSheet("color: #636d94; font-size: 11px;")
            title_col.addWidget(title)
            title_col.addWidget(subtitle)
            top_row.addLayout(title_col)

            top_row.addStretch()

            self.badge = QLabel("ЗАПУСК")
            self.badge.setStyleSheet("""
                color: #6ea8ff;
                background: rgba(110, 168, 255, 0.12);
                border: 1px solid rgba(110, 168, 255, 0.3);
                border-radius: 6px;
                padding: 3px 8px;
                font-size: 10px;
                font-weight: 700;
            """)
            top_row.addWidget(self.badge)
            layout.addLayout(top_row)

            layout.addStretch()

            # Status Message
            self.status_label = QLabel("Инициализация ядра и служб…")
            self.status_label.setStyleSheet("color: #9aa4cb; font-size: 12px; font-weight: 500;")
            layout.addWidget(self.status_label)

            # Progress Bar
            self.progress_bar = QProgressBar()
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(12)
            self.progress_bar.setTextVisible(False)
            self.progress_bar.setFixedHeight(5)
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    background-color: #070914;
                    border: 1px solid #1c2344;
                    border-radius: 2px;
                }
                QProgressBar::chunk {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0077aa, stop:1 #6ea8ff);
                    border-radius: 2px;
                }
            """)
            layout.addWidget(self.progress_bar)

            root.addWidget(card)

        def _on_tick(self):
            self.tick_count += 1

            if _check_health():
                self.timer.stop()
                self._on_success()
                return

            if self.tick_count >= self.max_ticks:
                self.timer.stop()
                self._on_timeout()
                return

            if self.tick_count < 10:
                val = min(35, 12 + self.tick_count * 3)
                self.status_label.setText("Запуск служб и EventBus…")
            elif self.tick_count < 25:
                val = min(72, 35 + (self.tick_count - 10) * 3)
                self.status_label.setText("Ожидание готовности шлюза ядра (порт 8765)…")
            else:
                val = min(92, 72 + (self.tick_count - 25))
                self.status_label.setText("Подключение к шлюзу API…")

            self.progress_bar.setValue(val)

        def _on_success(self):
            self.progress_bar.setValue(100)
            self.status_label.setText("Ядро подключено! Открытие интерфейса…")
            self.badge.setText("ГОТОВО")
            self.badge.setStyleSheet("""
                color: #3ee0b0;
                background: rgba(62, 224, 176, 0.12);
                border: 1px solid rgba(62, 224, 176, 0.35);
                border-radius: 6px;
                padding: 3px 8px;
                font-size: 10px;
                font-weight: 700;
            """)
            QTimer.singleShot(260, self._fade_out_and_exit)

        def _on_timeout(self):
            self.status_label.setText("Шлюз ядра не ответил вовремя")
            self.status_label.setStyleSheet("color: #f43f5e; font-size: 12px; font-weight: 500;")
            self.badge.setText("ОШИБКА")
            self.badge.setStyleSheet("""
                color: #f43f5e;
                background: rgba(244, 63, 94, 0.12);
                border: 1px solid rgba(244, 63, 94, 0.35);
                border-radius: 6px;
                padding: 3px 8px;
                font-size: 10px;
                font-weight: 700;
            """)
            QTimer.singleShot(1500, lambda: sys.exit(1))

        def _fade_out_and_exit(self):
            self._fade_anim = QPropertyAnimation(self, b"windowOpacity", self)
            self._fade_anim.setDuration(220)
            self._fade_anim.setStartValue(1.0)
            self._fade_anim.setEndValue(0.0)
            self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._fade_anim.finished.connect(lambda: sys.exit(0))
            self._fade_anim.start()

    window = DiscordSplashWindow()
    window.show()

    if "--dry-run" in sys.argv:
        QTimer.singleShot(50, lambda: sys.exit(0))

    return app.exec()


if __name__ == "__main__":
    if "--no-splash" in sys.argv:
        sys.exit(_cli_fallback())
    sys.exit(run_gui_splash())
