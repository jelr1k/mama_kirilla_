from __future__ import annotations

import logging
import os
import subprocess
import webbrowser
from typing import Any, Callable

try:
    from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
    from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon
    HAS_PYSIDE = True
except ImportError:
    HAS_PYSIDE = False
    QApplication = Any
    QSystemTrayIcon = Any
    QPixmap = Any

logger = logging.getLogger("jarvis.tray")


def create_tray_pixmap() -> Any:
    """Generate a clean vector-like tray icon pixmap."""
    if not HAS_PYSIDE:
        return None
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


def _restore_windows_window_by_title(keywords: tuple[str, ...]) -> bool:
    """Try to find and unhide existing Tauri desktop window on Windows via user32."""
    if os.name != "nt":
        return False
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32

        found = []

        def _enum_proc(hwnd, _):
            if not user32.IsWindow(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value
                for kw in keywords:
                    if kw.lower() in title.lower():
                        found.append(hwnd)
                        break
            return True

        enum_func = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(_enum_proc)
        user32.EnumWindows(enum_func, 0)

        if found:
            for hwnd in found:
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                user32.ShowWindow(hwnd, 5)  # SW_SHOW
                user32.SetForegroundWindow(hwnd)
            logger.info("restored_native_window_via_user32 count=%d", len(found))
            return True
    except Exception as exc:
        logger.debug("native_window_restore_failed error=%s", exc)
    return False


def create_system_tray(
    app: Any,
    backend: Any,
    open_ui_callback: Callable[[], Any] | None = None,
) -> Any:
    """Create a Windows system tray icon for headless background execution."""
    if not HAS_PYSIDE:
        logger.debug("PySide6 not available; system tray should be managed by Tauri")
        return None

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

        # 1. Send WebSocket event to unhide and focus window
        gateway = getattr(backend, "gateway", None)
        ws_sent = False
        if gateway and getattr(gateway, "hub", None):
            try:
                logger.info("sending_show_window_to_tauri")
                gateway.hub.broadcast({"type": "show_window"})
                ws_sent = bool(gateway.hub.has_clients)
            except Exception:
                pass

        # 2. Also try native Windows unhide/restore via Win32 API
        restored = _restore_windows_window_by_title((name, "Kirieshcka", "Kirieshka", "Jarvis"))
        if ws_sent or restored:
            return

        # 3. If no window and no active WebSocket clients, spawn the Tauri process
        root_dir = getattr(backend, "paths", None)
        base = root_dir.root if root_dir else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ui_dir = os.path.join(base, "ui")
        try:
            logger.info("launching_tauri_process_from_tray")
            flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            subprocess.Popen(
                [
                    "powershell",
                    "-WindowStyle",
                    "Hidden",
                    "-Command",
                    f"Start-Process cmd -ArgumentList '/c npx.cmd tauri dev' -WindowStyle Hidden -WorkingDirectory '{ui_dir}'",
                ],
                shell=False,
                creationflags=flags,
            )
            return
        except Exception:
            logger.exception("failed_to_launch_tauri_process")

        webbrowser.open("http://127.0.0.1:5174")

    open_action = menu.addAction("Открыть интерфейс")
    open_action.triggered.connect(handle_open_ui)

    menu.addSeparator()

    def handle_exit():
        logger.info("system_tray_exit_triggered")
        gateway = getattr(backend, "gateway", None)
        if gateway and getattr(gateway, "hub", None):
            try:
                gateway.hub.broadcast({"type": "exit_app"})
            except Exception:
                pass
        try:
            backend.shutdown()
        except Exception:
            logger.exception("backend_shutdown_failed_on_tray_exit")
        app.quit()

    exit_action = menu.addAction("Выход")
    exit_action.triggered.connect(handle_exit)

    tray.setContextMenu(menu)
    tray.activated.connect(
        lambda reason: handle_open_ui() if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick) else None
    )
    tray.show()
    logger.info("system_tray_initialized")
    return tray
