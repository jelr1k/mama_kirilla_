from __future__ import annotations

import logging
import webbrowser
from typing import Any, Callable

from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

logger = logging.getLogger("jarvis.tray")


def create_tray_pixmap() -> QPixmap:
    """Generate a clean vector-like tray icon pixmap."""
    pixmap = QPixmap(32, 32)
    pixmap.fill(QColor(0, 0, 0, 0))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # Outer cyan ring
    painter.setBrush(QColor(56, 189, 248))  # sky-400
    painter.setPen(QColor(14, 165, 233))   # sky-500
    painter.drawEllipse(3, 3, 26, 26)

    # Darker background core
    painter.setBrush(QColor(15, 23, 42))   # slate-900
    painter.setPen(QColor(0, 0, 0, 0))
    painter.drawEllipse(7, 7, 18, 18)

    # Center white pulse dot
    painter.setBrush(QColor(240, 249, 255))
    painter.drawEllipse(12, 12, 8, 8)

    painter.end()
    return pixmap


def create_system_tray(
    app: QApplication,
    backend: Any,
    open_ui_callback: Callable[[], Any] | None = None,
) -> QSystemTrayIcon | None:
    """Create a Windows system tray icon for headless background execution."""
    if not QSystemTrayIcon.isSystemTrayAvailable():
        logger.warning("System tray is not available on this platform.")
        return None

    tray = QSystemTrayIcon(QIcon(create_tray_pixmap()), app)
    name = getattr(backend, "config", {}).get("assistant_name", "Kirieshcka")
    tray.setToolTip(f"{name} v2 — Ядро активно (http://127.0.0.1:8765)")

    menu = QMenu()

    header_action = QAction(f"{name} Core v2 [Онлайн]", menu)
    header_action.setEnabled(False)
    menu.addAction(header_action)
    menu.addSeparator()

    def handle_open_ui():
        if open_ui_callback:
            try:
                open_ui_callback()
                return
            except Exception:
                logger.exception("custom_open_ui_callback_failed")
        webbrowser.open("http://127.0.0.1:5174")

    open_action = menu.addAction("Открыть интерфейс")
    open_action.triggered.connect(handle_open_ui)

    menu.addSeparator()

    def handle_exit():
        logger.info("system_tray_exit_triggered")
        try:
            backend.shutdown()
        except Exception:
            logger.exception("backend_shutdown_failed_on_tray_exit")
        app.quit()

    exit_action = menu.addAction("Выход")
    exit_action.triggered.connect(handle_exit)

    tray.setContextMenu(menu)
    tray.activated.connect(
        lambda reason: handle_open_ui() if reason == QSystemTrayIcon.Trigger else None
    )
    tray.show()
    logger.info("system_tray_initialized")
    return tray
