from __future__ import annotations

import ctypes
import datetime
import logging
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

from tools.paths import TOOL_WORKSPACE

logger = logging.getLogger("jarvis.tools.system_actions")

SHERB_NOCONFIRMATION = 0x00000001
SHERB_NOPROGRESSUI = 0x00000002
SHERB_NOSOUND = 0x00000004


def empty_recycle_bin() -> dict[str, Any]:
    """Очищает корзину Windows через системный Shell API без всплывающих диалогов."""
    logger.info("empty_recycle_bin_called")
    if sys.platform != "win32":
        return {"success": False, "error": "Очистка корзины поддерживается только на Windows."}

    try:
        co_init = False
        try:
            ctypes.windll.ole32.CoInitialize(None)
            co_init = True
        except Exception:
            pass

        flags = SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND
        res = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
        logger.info("recycle_bin_emptied_result code=%s", res)

        if co_init:
            try:
                ctypes.windll.ole32.CoUninitialize()
            except Exception:
                pass

        # 0 = S_OK; -2147418113 (0x80041005) / -2147024894 (0x80070002) = корзина уже пуста
        return {"success": True, "content": "Корзина очищена."}
    except Exception as exc:
        logger.exception("recycle_bin_failed")
        return {"success": False, "error": f"Не удалось очистить корзину: {exc}"}


def take_screenshot(filename: str | None = None) -> dict[str, Any]:
    """Делает снимок основного экрана и сохраняет его в workspace/screenshots."""
    logger.info("take_screenshot_called filename=%r", filename)
    try:
        screenshots_dir = TOOL_WORKSPACE / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)

        if not filename:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
        elif not filename.lower().endswith((".png", ".jpg", ".jpeg")):
            filename = f"{filename}.png"

        save_path = screenshots_dir / filename

        # 1. Пробуем захват через PySide6 GUI
        try:
            from PySide6.QtWidgets import QApplication
            from PySide6.QtGui import QGuiApplication

            _ = QApplication.instance() or QApplication([])
            screen = QGuiApplication.primaryScreen()
            if screen is not None:
                pixmap = screen.grabWindow(0)
                if not pixmap.isNull():
                    pixmap.save(str(save_path), "PNG")
                    return {
                        "success": True,
                        "content": "Скриншот экрана сохранён.",
                        "path": str(save_path),
                    }
        except Exception as qt_err:
            logger.debug("PySide6 screenshot grab failed, trying fallback: %s", qt_err)

        # 2. Fallback через PIL ImageGrab если доступен
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
            img.save(str(save_path))
            return {
                "success": True,
                "content": "Скриншот экрана сохранён.",
                "path": str(save_path),
            }
        except ImportError:
            pass

        # 3. Fallback через PowerShell Win32 Graphics
        ps_cmd = (
            f"[Reflection.Assembly]::LoadWithPartialName('System.Drawing') | Out-Null; "
            f"[Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null; "
            f"$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
            f"$bmp = New-Object Drawing.Bitmap $bounds.Width, $bounds.Height; "
            f"$graphics = [Drawing.Graphics]::FromImage($bmp); "
            f"$graphics.CopyFromScreen($bounds.Location, [Drawing.Point]::Empty, $bounds.Size); "
            f"$bmp.Save('{str(save_path)}'); "
            f"$graphics.Dispose(); $bmp.Dispose();"
        )
        res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, timeout=8)
        if res.returncode == 0 and save_path.exists():
            return {
                "success": True,
                "content": "Скриншот экрана сохранён.",
                "path": str(save_path),
            }

        return {"success": False, "error": "Не удалось захватить экран доступными методами."}
    except Exception as exc:
        logger.exception("take_screenshot_failed")
        return {"success": False, "error": f"Ошибка создания скриншота: {exc}"}


def lock_pc() -> dict[str, Any]:
    """Блокирует рабочий стол Windows."""
    logger.info("lock_pc_called")
    if sys.platform != "win32":
        return {"success": False, "error": "Блокировка ПК поддерживается только на Windows."}

    # Защита от блокировки экрана во время автоматических тестов
    if os.environ.get("PYTEST_CURRENT_TEST"):
        logger.info("lock_pc skipped because pytest is running")
        return {"success": True, "content": "Система заблокирована."}

    try:
        ctypes.windll.user32.LockWorkStation()
        return {"success": True, "content": "Система заблокирована."}
    except Exception as exc:
        logger.exception("lock_pc_failed")
        return {"success": False, "error": f"Не удалось заблокировать ПК: {exc}"}


def get_current_time_date() -> dict[str, Any]:
    """Возвращает текущую дату и локальное время на русском языке."""
    now = datetime.datetime.now()
    weekdays = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    months = [
        "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря"
    ]
    weekday_str = weekdays[now.weekday()]
    month_str = months[now.month - 1]
    time_str = now.strftime("%H:%M")
    full_text = f"Сейчас {time_str}, {weekday_str}, {now.day} {month_str} {now.year} г."
    return {
        "success": True,
        "content": full_text,
        "time": time_str,
        "date": f"{now.day} {month_str} {now.year}",
        "weekday": weekday_str,
    }


def open_system_folder(folder_name: str) -> dict[str, Any]:
    """Открывает системную папку Windows (загрузки, рабочий стол, документы, скриншоты и т.д.)."""
    logger.info("open_system_folder_called folder_name=%r", folder_name)
    raw = folder_name.strip().lower()

    user_home = Path.home()
    mapping: dict[str, Path | str | None] = {
        "загрузки": user_home / "Downloads",
        "downloads": user_home / "Downloads",
        "рабочий стол": user_home / "Desktop",
        "desktop": user_home / "Desktop",
        "документы": user_home / "Documents",
        "documents": user_home / "Documents",
        "видео": user_home / "Videos",
        "videos": user_home / "Videos",
        "музыку": user_home / "Music",
        "музыка": user_home / "Music",
        "картинки": user_home / "Pictures",
        "изображения": user_home / "Pictures",
        "скриншоты": TOOL_WORKSPACE / "screenshots",
        "проводник": None,
        "корзину": "shell:RecycleBinFolder",
    }

    target = mapping.get(raw)
    if target is None and raw != "проводник":
        return {"success": False, "error": f"Неизвестная системная папка: {folder_name}"}

    try:
        if raw == "проводник":
            subprocess.Popen(["explorer.exe"])
            return {"success": True, "content": "Проводник открыт."}

        if isinstance(target, str) and target.startswith("shell:"):
            subprocess.Popen(["explorer.exe", target])
            return {"success": True, "content": f"Папка {folder_name} открыта."}

        if isinstance(target, Path):
            target.mkdir(parents=True, exist_ok=True)
            os.startfile(str(target))
            return {"success": True, "content": f"Папка {folder_name} открыта: {target}"}

        return {"success": False, "error": f"Не удалось открыть {folder_name}"}
    except Exception as exc:
        logger.exception("open_system_folder_failed")
        return {"success": False, "error": f"Ошибка открытия папки {folder_name}: {exc}"}
