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
def _wait_window_message_loop(hwnd: int, timeout_ms: int = 500) -> None:
    """Синхронизация с очередью сообщений окна без слепого sleep."""
    if not hwnd:
        return
    try:
        SMTO_ABORTIFHUNG = 0x0002
        result = wintypes.DWORD()
        ctypes.windll.user32.SendMessageTimeoutW(
            hwnd, 0, 0, 0, SMTO_ABORTIFHUNG, timeout_ms, ctypes.byref(result)
        )
    except Exception:
        pass


def _wait_winapi_step(timeout_ms: int = 50) -> None:
    """Короткое ожидание событий очереди/потока через MsgWaitForMultipleObjects."""
    try:
        QS_ALLINPUT = 0x04FF
        ctypes.windll.user32.MsgWaitForMultipleObjects(0, None, False, timeout_ms, QS_ALLINPUT)
    except Exception:
        pass


def _try_click_apply_uia(hwnd: int) -> bool:
    """Пытается найти и нажать кнопку Применить через uiautomation."""
    try:
        import uiautomation as auto  # type: ignore[import-untyped]
    except Exception:
        return False

    try:
        root = auto.ControlFromHandle(hwnd)
        if not root:
            return False
        for name in ("Применить", "Apply", "btn_apply"):
            ctrl = root.ButtonControl(Name=name, searchDepth=6)
            if ctrl.Exists(0.2, 0.05):
                try:
                    invoke = ctrl.GetInvokePattern()
                    if invoke:
                        invoke.Invoke()
                        return True
                except Exception:
                    pass
                ctrl.Click(simulateMove=False)
                return True
    except Exception:
        return False
    return False


def _scaled_client_coords(user32: Any, hwnd: int, base_x: int, base_y: int) -> tuple[int, int]:
    """Масштабирует базовые клиентские координаты (96 DPI) под текущий DPI окна."""
    dpi = 96
    try:
        get_dpi = getattr(user32, "GetDpiForWindow", None)
        if get_dpi is not None:
            val = int(get_dpi(hwnd))
            if val > 0:
                dpi = val
    except Exception:
        dpi = 96
    scale = dpi / 96.0
    return int(round(base_x * scale)), int(round(base_y * scale))


# Client coordinates of the "btn_apply" button in 1280x750 layout (96 DPI)
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
    user32.OpenDesktopW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    user32.OpenDesktopW.restype = wintypes.HANDLE
    user32.SetThreadDesktop.argtypes = [wintypes.HANDLE]
    user32.SetThreadDesktop.restype = wintypes.BOOL
    user32.CloseDesktop.argtypes = [wintypes.HANDLE]
    user32.CloseDesktop.restype = wintypes.BOOL
    user32.WaitForInputIdle.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    user32.WaitForInputIdle.restype = wintypes.DWORD
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.ShowWindow.restype = wintypes.BOOL
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.restype = wintypes.BOOL
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.IsIconic.restype = wintypes.BOOL
    user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
    user32.ClientToScreen.restype = wintypes.BOOL
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.PostMessageW.restype = wintypes.BOOL

    # Гарантируем доступ к десктопу пользователя
    h_desk = None
    try:
        h_desk = user32.OpenDesktopW("default", 0, False, 0x01FF)
        if h_desk:
            user32.SetThreadDesktop(h_desk)
    except Exception as desk_err:
        logger.debug("set_thread_desktop error=%s", desk_err)

    try:
        return _apply_mouse_settings_impl(user32, auto_minimize_if_launched)
    finally:
        if h_desk:
            try:
                user32.CloseDesktop(h_desk)
            except Exception:
                pass


def _apply_mouse_settings_impl(user32: Any, auto_minimize_if_launched: bool) -> dict[str, Any]:

    is_running = _is_mouse_driver_running()
    launched = False

    if not is_running:
        exe_path = _resolve_fury_executable()
        if not exe_path or not exe_path.is_file():
            logger.error("fury_exe_not_found path=%s", exe_path)
            return {"success": False, "error": f"Исполняемый файл ZET Gaming Fury не найден ({DEFAULT_FURY_EXE})."}

        try:
            logger.info("launching_mouse_driver exe=%s", exe_path)
            proc = subprocess.Popen([str(exe_path)], cwd=str(exe_path.parent), shell=False)
            launched = True
            proc_handle = getattr(proc, "_handle", None)
            if proc_handle:
                try:
                    user32.WaitForInputIdle(int(proc_handle), 5000)
                except Exception:
                    pass
        except Exception as exc:
            logger.exception("launch_mouse_driver_failed")
            return {"success": False, "error": f"Не удалось запустить ZET Gaming Fury: {exc}"}

    # Поиск окна без слепого time.sleep
    hwnd = 0
    start_wait = time.monotonic()
    timeout = 6.0 if launched else 2.5

    while time.monotonic() - start_wait < timeout:
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
        _wait_winapi_step(80)

    if not hwnd:
        logger.error("fury_window_not_found launched=%s", launched)
        return {"success": False, "error": "Окно ZET GAMING Fury не найдено."}

    was_visible = bool(user32.IsWindowVisible(hwnd) and not user32.IsIconic(hwnd))

    # Восстанавливаем окно и выводим на передний план
    SW_RESTORE = 9
    user32.ShowWindow(hwnd, SW_RESTORE)
    user32.SetForegroundWindow(hwnd)
    _wait_window_message_loop(hwnd, 500)

    # 1. Пробуем нажать кнопку через UIAutomation
    if not _try_click_apply_uia(hwnd):
        # 2. DPI-адаптивный фоллбэк: масштабируем клиентские координаты под DPI окна
        client_x, client_y = _scaled_client_coords(
            user32, hwnd, BUTTON_APPLY_CLIENT_X, BUTTON_APPLY_CLIENT_Y
        )
        pt = wintypes.POINT(client_x, client_y)
        user32.ClientToScreen(hwnd, ctypes.byref(pt))

        orig_pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(orig_pt))

        try:
            user32.SetCursorPos(pt.x, pt.y)
            _wait_window_message_loop(hwnd, 200)

            MOUSEEVENTF_LEFTDOWN = 0x0002
            MOUSEEVENTF_LEFTUP = 0x0004
            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            _wait_window_message_loop(hwnd, 200)
        finally:
            user32.SetCursorPos(orig_pt.x, orig_pt.y)

        # Дополнительно дублируем Win32 WM_LBUTTONDOWN/UP
        WM_LBUTTONDOWN = 0x0201
        WM_LBUTTONUP = 0x0202
        MK_LBUTTON = 0x0001
        l_param = (client_y << 16) | (client_x & 0xFFFF)
        user32.PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, l_param)
        user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, l_param)
        _wait_window_message_loop(hwnd, 300)

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
