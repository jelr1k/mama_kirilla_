from __future__ import annotations

import ctypes
from ctypes import wintypes
import logging
import os
from pathlib import Path
import subprocess
import time
from typing import Any
import winreg

import psutil

logger = logging.getLogger("jarvis.tools.mouse_driver")

DEFAULT_FURY_EXE = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Fury3327BK" / "MouseDriver.exe"
WINDOW_CLASS = "Mouse Driver"
WINDOW_TITLE = "ZET GAMING Fury 3327 BK"
# Client coordinates of the "btn_apply" button in 1280x750 layout
BUTTON_APPLY_CLIENT_X = 192
BUTTON_APPLY_CLIENT_Y = 520


def _resolve_fury_executable() -> Path | None:
    """Определяет путь к исполняемому файлу ZET Gaming Fury 3327 BK."""
    if DEFAULT_FURY_EXE.is_file():
        return DEFAULT_FURY_EXE

    # Проверяем реестр Uninstall
    for root_key in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for subkey in (
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Fury3327BK",
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Fury3327BK",
        ):
            try:
                with winreg.OpenKey(root_key, subkey) as key:
                    loc, _ = winreg.QueryValueEx(key, "InstallLocation")
                    cand = Path(loc) / "MouseDriver.exe"
                    if cand.is_file():
                        return cand
            except OSError:
                pass

    return None


def _is_mouse_driver_running() -> bool:
    """Проверяет, запущен ли процесс MouseDriver."""
    for proc in psutil.process_iter(["name"]):
        try:
            name = (proc.info.get("name") or "").lower()
            if name in ("mousedriver.exe", "mousedriver"):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False


def apply_mouse_settings(auto_minimize_if_launched: bool = True) -> dict[str, Any]:
    """Применяет настройки в приложении ZET Gaming Fury 3327 BK.

    Если программа выключена — запускает её, дожидается открытия окна и нажимает «Применить».
    Если программа уже включена — активирует её окно и нажимает «Применить».
    """
    logger.info("apply_mouse_settings_called")
    if os.name != "nt":
        return {"success": False, "error": "Функция доступна только на Windows."}

    user32 = ctypes.windll.user32

    # Гарантируем доступ к десктопу пользователя
    try:
        h_desk = user32.OpenDesktopW("default", 0, False, 0x01FF)
        if h_desk:
            user32.SetThreadDesktop(h_desk)
    except Exception as desk_err:
        logger.debug("set_thread_desktop error=%s", desk_err)

    is_running = _is_mouse_driver_running()
    launched = False

    if not is_running:
        exe_path = _resolve_fury_executable()
        if not exe_path or not exe_path.is_file():
            logger.error("fury_exe_not_found path=%s", exe_path)
            return {"success": False, "error": f"Исполняемый файл ZET Gaming Fury не найден ({DEFAULT_FURY_EXE})."}

        try:
            logger.info("launching_mouse_driver exe=%s", exe_path)
            subprocess.Popen([str(exe_path)], cwd=str(exe_path.parent), shell=False)
            launched = True
        except Exception as exc:
            logger.exception("launch_mouse_driver_failed")
            return {"success": False, "error": f"Не удалось запустить ZET Gaming Fury: {exc}"}

    # Поиск окна
    hwnd = 0
    start_wait = time.time()
    timeout = 6.0 if launched else 2.5

    while time.time() - start_wait < timeout:
        hwnd = user32.FindWindowW(WINDOW_CLASS, WINDOW_TITLE)
        if not hwnd:
            # Fallback перебор окон по заголовку
            found_hwnd = 0

            def _enum_proc(h, _):
                nonlocal found_hwnd
                length = user32.GetWindowTextLengthW(h)
                if length:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(h, buf, length + 1)
                    title = buf.value
                    if "Fury 3327" in title or "ZET GAMING Fury" in title:
                        found_hwnd = h
                        return False
                return True

            enum_cb = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)(_enum_proc)
            user32.EnumWindows(enum_cb, 0)
            hwnd = found_hwnd

        if hwnd:
            break
        time.sleep(0.2)

    if not hwnd:
        logger.error("fury_window_not_found launched=%s", launched)
        return {"success": False, "error": "Окно ZET GAMING Fury не найдено."}

    was_visible = bool(user32.IsWindowVisible(hwnd) and not user32.IsIconic(hwnd))

    # Восстанавливаем окно и выводим на передний план
    SW_RESTORE = 9
    user32.ShowWindow(hwnd, SW_RESTORE)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.15)

    # Вычисляем экранные координаты кнопки btn_apply
    pt = wintypes.POINT(BUTTON_APPLY_CLIENT_X, BUTTON_APPLY_CLIENT_Y)
    user32.ClientToScreen(hwnd, ctypes.byref(pt))

    # Запоминаем текущую позицию курсора пользователя
    orig_pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(orig_pt))

    try:
        # Клик через перемещение курсора + mouse_event
        user32.SetCursorPos(pt.x, pt.y)
        time.sleep(0.04)

        MOUSEEVENTF_LEFTDOWN = 0x0002
        MOUSEEVENTF_LEFTUP = 0x0004
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.06)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        time.sleep(0.04)
    finally:
        # Гарантированно возвращаем мышь на место
        user32.SetCursorPos(orig_pt.x, orig_pt.y)

    # Дополнительно дублируем Win32 WM_LBUTTONDOWN/UP
    WM_LBUTTONDOWN = 0x0201
    WM_LBUTTONUP = 0x0202
    MK_LBUTTON = 0x0001
    l_param = (BUTTON_APPLY_CLIENT_Y << 16) | (BUTTON_APPLY_CLIENT_X & 0xFFFF)
    user32.PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, l_param)
    time.sleep(0.02)
    user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, l_param)

    time.sleep(0.2)

    # Если окно только что запущено или до этого было скрыто/свернуто в трей
    if auto_minimize_if_launched and (launched or not was_visible):
        SW_MINIMIZE = 6
        user32.ShowWindow(hwnd, SW_MINIMIZE)

    status_detail = "запущена и настройки применены" if launched else "настройки применены"
    logger.info("apply_mouse_settings_success launched=%s", launched)
    return {
        "success": True,
        "content": f"Готово, программа ZET Gaming Fury {status_detail}.",
        "launched": launched,
    }
