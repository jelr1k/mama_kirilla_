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
    tray.setToolTip(f"{name} v2 - Ядро активно")

    menu = QMenu()

    header_action = QAction(f"{name} Core v2 [Активен]", menu)
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

        # 1. If Tauri is already connected via WebSocket, send command to unhide and focus window
        gateway = getattr(backend, "gateway", None)
        if gateway and getattr(gateway, "hub", None) and gateway.hub.has_clients:
            logger.info("sending_show_window_to_tauri")
            gateway.hub.broadcast({"type": "show_window"})
            return

        # 2. If Tauri process was terminated, launch it
        import subprocess
        root_dir = getattr(backend, "paths", None)
        base = root_dir.root if root_dir else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ui_dir = os.path.join(base, "ui")
        try:
            logger.info("launching_tauri_process_from_tray")
            subprocess.Popen(["cmd.exe", "/c", "npx.cmd tauri dev"], cwd=ui_dir, shell=False)
            return
        except Exception:
            logger.exception("failed_to_launch_tauri_process")

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
