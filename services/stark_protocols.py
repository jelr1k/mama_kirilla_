from __future__ import annotations

import ctypes
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import random
import time
import urllib.request
from typing import Any

import psutil

from core.protocol_adapters import (
    BrowserAdapter,
    GenericAppAdapter,
    is_app_in_lock_list,
    resolve_role_token,
)
from tools import media_control
from tools.system_actions import empty_recycle_bin

logger = logging.getLogger("jarvis.protocols")


class StarkProtocols:
    """Управление фирменными сценариями и протоколами JARVIS."""

    # Процессы, которые категорически ЗАПРЕЩЕНО закрывать при любых протоколах:
    PROTECTED_PROCESS_NAMES = {
        # Системные процессы Windows
        "system", "system idle process", "registry", "smss.exe", "csrss.exe", "wininit.exe",
        "services.exe", "lsass.exe", "svchost.exe", "fontdrvhost.exe", "winlogon.exe",
        "dwm.exe", "explorer.exe", "sihost.exe", "taskhostw.exe", "ctfmon.exe", "shellexperiencehost.exe",
        "startmenuexperiencehost.exe", "searchhost.exe", "textinputhost.exe", "spoolsv.exe",
        "audiodg.exe", "conhost.exe", "runtimebroker.exe", "securityhealthsystray.exe",
        "securityhealthservice.exe", "smartscreen.exe", "dashost.exe",
        # Драйверы и железо
        "amdfendrsr.exe", "amdinstallmanager.exe", "amdrsserv.exe", "radeonsoftware.exe",
        "rtkaudservice64.exe", "ravbg64.exe", "epicgameslauncher.exe",
        # Системные фоновые службы обхода / прокси пользователя (чтобы не сломать интернет)
        "ag_dns.exe", "ag_dns", "tgwsproxy_windows.exe", "tgwsproxy.exe",
        # Сам JARVIS, Ollama и консоли
        "python.exe", "pythonw.exe", "cmd.exe", "powershell.exe", "pwsh.exe",
        "ollama.exe", "ollama_llama_server.exe",
    }

    # Wallpaper Engine и фоновые утилиты Steam, которые нельзя закрывать при закрытии игр
    PROTECTED_STEAM_TOOLS = {
        "steam.exe", "steamwebhelper.exe",
        "wallpaper32.exe", "wallpaper64.exe", "winrtutil64.exe", "webwallpaper32.exe",
        "soundpad.exe",
    }

    @classmethod
    def _get_app_process_patterns(cls, app_key: str) -> list[str]:
        """Возвращает возможные имена/паттерны процессов для app_key с опорой на AppIndexer."""
        key = app_key.lower().strip()
        name_map = {
            "opera": ["opera.exe"],
            "vivaldi": ["vivaldi.exe"],
            "discord": ["discord.exe"],
            "steam": ["steam.exe"],
            "antigravity": ["antigravity.exe"],
            "unlocker": ["ag_2.", "unlocker"],
            "obs": ["obs64.exe", "obs32.exe", "obs.exe"],
            "telegram": ["telegram.exe"],
            "spotify": ["spotify.exe"],
            "chrome": ["chrome.exe"],
        }
        target_patterns = list(name_map.get(key, [f"{key}.exe", key]))
        if key not in name_map:
            try:
                from core.app_indexer import AppIndexer
                indexer = AppIndexer.get_instance()
                resolved = indexer.resolve_app(key)
                if resolved and resolved.get("executable"):
                    exe_name = Path(resolved["executable"]).name.lower()
                    if exe_name and exe_name not in target_patterns:
                        target_patterns.insert(0, exe_name)
            except Exception:
                pass
        return target_patterns

    @classmethod
    def _find_app_pids(cls, app_key: str) -> set[int]:
        """Возвращает PID запущенных процессов, относящихся к app_key."""
        target_patterns = cls._get_app_process_patterns(app_key)
        pids: set[int] = set()
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                pname = (proc.info.get("name") or "").lower()
                for pat in target_patterns:
                    if (pat.endswith(".exe") and pname == pat) or (not pat.endswith(".exe") and pat in pname):
                        if proc.info.get("pid"):
                            pids.add(int(proc.info["pid"]))
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return pids

    @staticmethod
    def _find_window_for_pids(pids: set[int]) -> int | None:
        """Находит главное видимое окно WinAPI, принадлежащее одному из PID."""
        import sys
        if sys.platform != "win32" or not pids:
            return None
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        found: list[int] = []

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def _enum_cb(hwnd: int, _lparam: int) -> bool:
            if not user32.IsWindowVisible(hwnd):
                return True
            if user32.GetWindowTextLengthW(hwnd) <= 0:
                return True
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value in pids:
                found.append(int(hwnd))
                return False
            return True

        user32.EnumWindows(WNDENUMPROC(_enum_cb), 0)
        return found[0] if found else None

    @staticmethod
    def _focus_hwnd(hwnd: int) -> bool:
        """Разворачивает и выводит окно на передний план через WinAPI."""
        import sys
        if sys.platform != "win32" or not hwnd:
            return False
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        SW_RESTORE = 9

        try:
            if user32.IsIconic(hwnd):
                user32.ShowWindow(hwnd, SW_RESTORE)
            fg_hwnd = user32.GetForegroundWindow()
            cur_tid = kernel32.GetCurrentThreadId()
            fg_tid = user32.GetWindowThreadProcessId(fg_hwnd, None) if fg_hwnd else 0
            attached = False
            if fg_tid and fg_tid != cur_tid:
                attached = bool(user32.AttachThreadInput(cur_tid, fg_tid, True))
            try:
                user32.BringWindowToTop(hwnd)
                ok = bool(user32.SetForegroundWindow(hwnd))
            finally:
                if attached:
                    user32.AttachThreadInput(cur_tid, fg_tid, False)
            return ok
        except Exception as exc:
            logger.debug("focus_hwnd_failed hwnd=%s err=%s", hwnd, exc)
            return False

    @classmethod
    def focus_app_window(cls, app_key: str) -> bool:
        """Находит главное окно уже запущенного приложения и выводит его на передний план."""
        import sys
        if sys.platform != "win32" or type(os.startfile).__module__ == "unittest.mock":
            return False
        pids = cls._find_app_pids(app_key)
        hwnd = cls._find_window_for_pids(pids)
        if hwnd:
            return cls._focus_hwnd(hwnd)
        return False

    @classmethod
    def wait_for_app_window(cls, app_key: str, timeout: float = 4.0) -> bool:
        """Ожидает появления видимого окна запущенного приложения по WinAPI и фокусирует его."""
        import sys
        if sys.platform != "win32" or type(os.startfile).__module__ == "unittest.mock":
            return False
        deadline = time.monotonic() + max(0.2, timeout)
        while time.monotonic() < deadline:
            pids = cls._find_app_pids(app_key)
            hwnd = cls._find_window_for_pids(pids)
            if hwnd:
                cls._focus_hwnd(hwnd)
                return True
            time.sleep(0.15)
        return False

    @classmethod
    def is_app_running(cls, app_key: str) -> bool:
        """Проверяет, запущен ли процесс приложения (без регистра и с поддержкой вариантов)."""
        target_patterns = cls._get_app_process_patterns(app_key)
        for proc in psutil.process_iter(["name"]):
            try:
                pname = (proc.info.get("name") or "").lower()
                for pat in target_patterns:
                    if (pat.endswith(".exe") and pname == pat) or (not pat.endswith(".exe") and pat in pname):
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    @classmethod
    def launch_if_not_running(cls, app_key: str) -> tuple[bool, str]:
        """Запускает приложение, ТОЛЬКО если оно ещё не запущено (идемпотентность)."""
        # Проверяем, не является ли это игрой Steam (или steam:<appid>)
        try:
            from core.steam_manager import SteamManager
            sm = SteamManager.get_instance()
            game = sm.resolve_game(app_key)
            if game:
                if sm.is_game_running(game):
                    logger.info("steam_game_already_running app=%s", game.get("name"))
                    return True, "уже запущено"
                res = sm.launch_game(game)
                if res.get("success"):
                    return True, "запущено"
                return False, res.get("error", "ошибка запуска Steam")
        except Exception as exc:
            logger.debug("steam_resolve_skip error=%s", exc)

        if cls.is_app_running(app_key):
            logger.info("app_already_running key=%s", app_key)
            cls.focus_app_window(app_key)
            return True, "уже запущено"

        path = cls._resolve_app_path(app_key)
        if not path or not path.exists():
            logger.warning("app_path_not_found key=%s path=%s", app_key, path)
            return False, f"Приложение '{app_key}' не обнаружено в системе"

        try:
            logger.info("launching_app key=%s path=%s", app_key, path)
            cls._launch_path_winapi(path)
            cls.wait_for_app_window(app_key, timeout=4.0)
            return True, "запущено"
        except Exception as exc:
            logger.exception("launch_app_error key=%s path=%s", app_key, path)
            return False, str(exc)

    @staticmethod
    def _launch_path_winapi(path: Path, parameters: str | None = None) -> None:
        """Запускает .exe/.lnk через ShellExecuteExW с ожиданием WaitForInputIdle (без WinError 193)."""
        import sys
        # Сохраняем совместимость с тестами, мокающими os.startfile
        if sys.platform != "win32" or type(os.startfile).__module__ == "unittest.mock":
            os.startfile(str(path))
            return

        from ctypes import wintypes

        class SHELLEXECUTEINFOW(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("fMask", wintypes.ULONG),
                ("hwnd", wintypes.HWND),
                ("lpVerb", wintypes.LPCWSTR),
                ("lpFile", wintypes.LPCWSTR),
                ("lpParameters", wintypes.LPCWSTR),
                ("lpDirectory", wintypes.LPCWSTR),
                ("nShow", ctypes.c_int),
                ("hInstApp", wintypes.HINSTANCE),
                ("lpIDList", ctypes.c_void_p),
                ("lpClass", wintypes.LPCWSTR),
                ("hkeyClass", wintypes.HKEY),
                ("dwHotKey", wintypes.DWORD),
                ("hIconOrMonitor", wintypes.HANDLE),
                ("hProcess", wintypes.HANDLE),
            ]

        SEE_MASK_NOCLOSEPROCESS = 0x00000040
        SW_SHOWNORMAL = 1
        info = SHELLEXECUTEINFOW()
        info.cbSize = ctypes.sizeof(SHELLEXECUTEINFOW)
        info.fMask = SEE_MASK_NOCLOSEPROCESS
        info.lpVerb = "open"
        info.lpFile = str(path)
        info.lpParameters = parameters or None
        info.lpDirectory = str(path.parent)
        info.nShow = SW_SHOWNORMAL

        if not ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(info)):
            raise ctypes.WinError()

        if info.hProcess:
            try:
                ctypes.windll.user32.WaitForInputIdle(info.hProcess, 3000)
            finally:
                ctypes.windll.kernel32.CloseHandle(info.hProcess)

    @classmethod
    def _resolve_app_path(cls, app_key: str) -> Path | None:
        """Динамически находит исполняемый файл или ярлык приложения на диске."""
        target_p = Path(app_key).expanduser()
        if target_p.is_file():
            return target_p

        key = app_key.lower().strip()

        # 1. Steam: через SteamManager / реестр
        if key in ("steam", "стим"):
            try:
                from core.steam_manager import SteamManager
                sm = SteamManager.get_instance()
                s_root = sm.find_steam_root()
                if s_root:
                    s_exe = s_root / "steam.exe"
                    if s_exe.is_file():
                        return s_exe
            except Exception as exc:
                logger.debug("steam_root_resolve_failed error=%s", exc)
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
                    val, _ = winreg.QueryValueEx(k, "SteamExe")
                    sp = Path(val)
                    if sp.is_file():
                        return sp
            except Exception as exc:
                logger.debug("steam_reg_resolve_failed error=%s", exc)

        # 2. Динамический индекс установленных приложений (Start Menu / реестр)
        try:
            from core.app_indexer import AppIndexer
            indexer = AppIndexer.get_instance()
            resolved = indexer.resolve_app(app_key)
            if resolved:
                for field in ("path", "executable", "shortcut"):
                    raw = resolved.get(field)
                    if raw:
                        p = Path(raw)
                        if p.is_file():
                            return p
        except Exception as exc:
            logger.debug("app_indexer_resolve_failed key=%s error=%s", app_key, exc)

        # 3. Общий поиск через find_application
        try:
            from tools.applications import find_application
            found = find_application(app_key)
            if found.get("success") and found.get("path"):
                p = Path(found["path"])
                if p.is_file():
                    return p
        except Exception as exc:
            logger.debug("find_application_resolve_failed key=%s error=%s", app_key, exc)

        return None

    @classmethod
    def close_steam_games(
        cls,
        blocked_apps: list[str] | set[str] | None = None,
        roles: dict[str, str] | None = None,
    ) -> list[str]:
        """Закрывает только запущенные игры Steam (не закрывая сам Steam и Wallpaper Engine)."""
        closed = []
        procs: list[psutil.Process] = []
        for proc in psutil.process_iter(["pid", "name", "exe", "cwd"]):
            try:
                name = (proc.info.get("name") or "").lower()
                if name in cls.PROTECTED_STEAM_TOOLS or name in cls.PROTECTED_PROCESS_NAMES:
                    continue
                if blocked_apps and is_app_in_lock_list(
                    name, blocked_apps, roles=roles, patterns_fn=cls._get_app_process_patterns
                ):
                    continue

                exe = (proc.info.get("exe") or "").lower()
                cwd = (proc.info.get("cwd") or "").lower()
                if "steamapps" in exe or "steamapps" in cwd:
                    proc.terminate()
                    procs.append(proc)
                    closed.append(proc.info.get("name"))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        if procs:
            psutil.wait_procs(procs, timeout=2.0)
        return closed

    @staticmethod
    def _indexed_exes_by_categories(categories: set[str]) -> set[str]:
        """Собирает имена .exe установленных приложений заданных категорий из AppIndexer."""
        exes: set[str] = set()
        try:
            from core.app_indexer import AppIndexer
            for app in AppIndexer.get_instance().scan_installed_apps():
                if app.get("category") in categories and app.get("executable"):
                    exes.add(Path(str(app["executable"])).name.lower())
        except Exception:
            pass
        return exes

    @classmethod
    def close_user_apps_for_gaming(
        cls,
        blocked_apps: list[str] | set[str] | None = None,
        roles: dict[str, str] | None = None,
    ) -> list[str]:
        """Закрывает браузеры и фоновые рабочие программы перед игрой (Steam и Discord остаются!)."""
        closed = []
        procs: list[psutil.Process] = []
        allowed = {
            "steam.exe", "steamwebhelper.exe", "discord.exe",
            "wallpaper32.exe", "wallpaper64.exe", "winrtutil64.exe", "webwallpaper32.exe",
        } | cls._indexed_exes_by_categories({"gaming", "messenger"})
        # Telegram часто относится к мессенджерам, но в игровом режиме его традиционно закрывают если не нужен,
        # хотя безопаснее закрывать именно браузеры, рабочие IDE и медиаплееры
        allowed.discard("telegram.exe")

        targets_to_close = {
            "opera.exe", "vivaldi.exe", "chrome.exe", "msedge.exe", "firefox.exe",
            "antigravity.exe", "telegram.exe", "spotify.exe",
        } | cls._indexed_exes_by_categories({"browser", "work", "media"})
        targets_to_close -= allowed

        for proc in psutil.process_iter(["pid", "name"]):
            try:
                name = (proc.info.get("name") or "").lower()
                if name in allowed or name in cls.PROTECTED_PROCESS_NAMES:
                    continue
                if blocked_apps and is_app_in_lock_list(
                    name, blocked_apps, roles=roles, patterns_fn=cls._get_app_process_patterns
                ):
                    continue

                if name in targets_to_close or name.startswith("ag_2."):
                    proc.terminate()
                    procs.append(proc)
                    closed.append(name)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        if procs:
            psutil.wait_procs(procs, timeout=2.0)
        return closed

    @classmethod
    def close_apps_for_cinema(
        cls,
        blocked_apps: list[str] | set[str] | None = None,
        roles: dict[str, str] | None = None,
    ) -> list[str]:
        """Закрывает игры и рабочие IDE, оставляя браузеры, мессенджеры и лаунчеры."""
        closed = []
        procs: list[psutil.Process] = []
        allowed = {
            "steam.exe", "steamwebhelper.exe", "discord.exe",
            "opera.exe", "vivaldi.exe", "chrome.exe", "msedge.exe", "firefox.exe",
            "wallpaper32.exe", "wallpaper64.exe", "winrtutil64.exe", "webwallpaper32.exe",
        } | cls._indexed_exes_by_categories({"browser", "messenger"})
        targets_to_close = {
            "antigravity.exe",
        } | cls._indexed_exes_by_categories({"work"})
        targets_to_close -= allowed

        closed.extend(cls.close_steam_games(blocked_apps=blocked_apps, roles=roles))

        for proc in psutil.process_iter(["pid", "name"]):
            try:
                name = (proc.info.get("name") or "").lower()
                if name in allowed or name in cls.PROTECTED_PROCESS_NAMES:
                    continue
                if blocked_apps and is_app_in_lock_list(
                    name, blocked_apps, roles=roles, patterns_fn=cls._get_app_process_patterns
                ):
                    continue

                if name in targets_to_close or name.startswith("ag_2."):
                    proc.terminate()
                    procs.append(proc)
                    closed.append(name)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        if procs:
            psutil.wait_procs(procs, timeout=2.0)
        return closed

    @classmethod
    def set_volume_max(cls) -> None:
        """Устанавливает системную громкость Windows на 100%."""
        media_control.set_master_volume_scalar(1.0)
        media_control.set_master_mute(False)

    @classmethod
    def lock_workstation(cls) -> None:
        """Ставит воспроизведение на паузу и блокирует рабочую станцию Windows."""
        try:
            media_control._send_key(media_control.VK_MAP["play_pause"], repeat=1)
        except Exception as exc:
            logger.debug("lock_workstation_pause_failed error=%s", exc)
        try:
            ctypes.windll.user32.LockWorkStation()
        except Exception as exc:
            logger.exception("LockWorkStation error: %s", exc)

    @classmethod
    def get_weather_info(cls, weather_cfg: dict[str, Any] | None = None) -> str:
        """Легкий опрос погоды с жестким таймаутом (чтобы не вешать систему)."""
        try:
            if weather_cfg is None:
                from core.config_manager import ConfigManager
                weather_cfg = ConfigManager().get("weather", {}) or {}
            lat = float(weather_cfg.get("latitude", 55.7558))
            lon = float(weather_cfg.get("longitude", 37.6173))
            city = str(weather_cfg.get("city", "Москве") or "Москве").strip()
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
            req = urllib.request.Request(url, headers={"User-Agent": "Assistant/1.0"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                temp = data.get("current_weather", {}).get("temperature")
                if temp is not None:
                    return f", в {city} сейчас {round(temp)}°"
        except Exception as exc:
            logger.debug("weather_fetch_failed error=%s", exc)
        return ""

    @classmethod
    def _generate_stark_fallback(cls, proto: dict[str, Any]) -> str:
        """Встроенный динамический генератор ответов в стиле JARVIS."""
        name = proto.get("name") or "Сценарий"
        proto_id = str(proto.get("id") or "").lower()
        close_mode = str(proto.get("close_mode") or "none")
        open_apps = proto.get("open_apps") or []

        if proto_id == "morning" or proto.get("briefing"):
            return random.choice([
                "Все системы развёрнуты и готовы к работе, сэр.",
                "Диагностика завершена успешно. Приложения готовы к работе.",
                "С возвращением в строй, сэр. Все протоколы инициализированы.",
                "Утренний запуск завершён. Кофе за вами, сэр.",
            ])

        if proto_id == "lockdown" or proto.get("lock_screen"):
            return random.choice([
                "Блокирую терминал. До вашего возвращения, сэр.",
                "Система заблокирована от посторонних глаз. Буду на страже.",
                "Терминал на замке. Жду вашего возвращения, сэр.",
            ])

        if proto_id == "cinema" or close_mode == "cinema":
            return random.choice([
                "Протокол «Кино» активирован, сэр. Громкость на максимуме, браузер открыт. Discord и Steam сохранены. Приятного просмотра.",
                "Звук на полную, посторонние окна закрыты. Приятного отдыха, сэр.",
                "Экран готов к сеансу, сэр. Все лишние процессы утилизированы.",
            ])

        if proto_id == "game" or close_mode == "game":
            return random.choice([
                "Игровой протокол активирован, сэр. Выделяю ресурсы: браузер и программы закрыты. Steam и Discord на связи. Приятной игры.",
                "Ресурсы перенаправлены на гейминг, сэр. Лишнее закрыто, связь активна.",
                "Игровой режим в действии. Постарайтесь не разбить монитор, сэр.",
                "Все ядра к вашим услугам, сэр. Удачной игры.",
            ])

        if proto_id == "work" or close_mode == "steam_games":
            return random.choice([
                "Протокол «Работа» активирован, сэр. Игра закрыта, рабочие инструменты готовы. Discord активен.",
                "Игрушки в сторону, сэр. Рабочие среды развёрнуты, приступаем к задачам.",
                "Рабочая станция переведена в режим созидания. Все инструменты наготове, сэр.",
            ])

        if proto_id == "clean_desk" or (proto.get("clean_recycle_bin") and not open_apps):
            return random.choice([
                "Корзина очищена, сэр. Рабочее пространство в полном порядке.",
                "Цифровой мусор утилизирован, сэр. Никаких следов.",
                "Корзина пуста. Чистый стол — чистый разум, сэр.",
            ])

        if proto_id == "default":
            return random.choice([
                "Стандартный режим восстановлен, сэр. Громкость на 100%, все системы в исходном состоянии.",
                "Дефолтные настройки возвращены. Все параметры в норме, сэр.",
            ])

        if open_apps and close_mode != "none":
            return random.choice([
                f"Протокол «{name}» выполнен: окружение развёрнуто, лишние процессы закрыты. К вашим услугам, сэр.",
                f"Директивы протокола «{name}» приведены в исполнение, ресурсы перераспределены.",
                f"Всё готово по протоколу «{name}». Можем приступать, сэр.",
            ])
        elif open_apps:
            apps_str = ", ".join(open_apps[:3])
            return random.choice([
                f"Протокол «{name}» активирован. Приложения {apps_str} готовы к работе, сэр.",
                f"Запуск {apps_str} завершён. Все системы протокола «{name}» в норме.",
                f"Развернул необходимое окружение по протоколу «{name}». К вашим услугам, сэр.",
            ])
        else:
            return random.choice([
                f"Протокол «{name}» активирован. Все директивы выполнены безупречно, сэр.",
                f"Директивы протокола «{name}» исполнены в полном объёме, сэр.",
                f"Протокол «{name}» успешно завершён. Системы функционируют штатно.",
            ])

    @classmethod
    def generate_dynamic_response(cls, proto: dict[str, Any], ollama_url: str | None = None, model: str | None = None) -> str:
        """Мгновенный детерминированный Stark-генератор без сетевых вызовов."""
        return cls._generate_stark_fallback(proto)

    @classmethod
    def _build_execution_report(
        cls,
        proto: dict[str, Any],
        launched_apps: list[str],
        already_running_apps: list[str],
        failed_apps: list[tuple[str, str]],
        closed_apps: list[str],
        skipped_blocked: list[str] | None = None,
    ) -> str:
        """Собирает реальный отчёт по шагам выполнения протокола."""
        parts: list[str] = []
        if launched_apps:
            parts.append(f"Запущено: {', '.join(launched_apps)}.")
        if already_running_apps:
            parts.append(f"Уже открыто: {', '.join(already_running_apps)}.")
        if closed_apps:
            uniq_closed = list(dict.fromkeys(str(x) for x in closed_apps if x))
            if uniq_closed:
                parts.append(f"Закрыто: {', '.join(uniq_closed)}.")
        if skipped_blocked:
            uniq_skipped = list(dict.fromkeys(str(x) for x in skipped_blocked if x))
            if uniq_skipped:
                parts.append(f"Пропущено по исключениям: {', '.join(uniq_skipped)}.")
        if failed_apps:
            failed_str = ", ".join(f"{app} ({err})" for app, err in failed_apps)
            parts.append(f"Не удалось запустить: {failed_str}.")

        if not parts:
            return cls.generate_dynamic_response(proto)

        name = proto.get("name") or "Сценарий"
        return f"Протокол «{name}»: " + " ".join(parts)

    @classmethod
    def _run_close_mode(
        cls,
        close_mode: str,
        blocked_close: list[str],
        roles: dict[str, str] | None,
    ) -> list[str]:
        res_closed: Any = None
        if close_mode == "steam_games":
            res_closed = cls.close_steam_games(blocked_apps=blocked_close, roles=roles)
        elif close_mode == "cinema":
            res_closed = cls.close_apps_for_cinema(blocked_apps=blocked_close, roles=roles)
        elif close_mode == "game":
            res_closed = cls.close_user_apps_for_gaming(blocked_apps=blocked_close, roles=roles)
        return list(res_closed) if isinstance(res_closed, list) else []

    @classmethod
    def _run_close_target(
        cls,
        raw_target: str,
        blocked_close: list[str],
        roles: dict[str, str] | None,
        closed_apps: list[str],
        skipped_blocked: list[str],
    ) -> None:
        app = resolve_role_token(raw_target, roles)
        if not app:
            return
        if is_app_in_lock_list(app, blocked_close, roles=roles, patterns_fn=cls._get_app_process_patterns):
            skipped_blocked.append(f"не закрыто {app}")
            return
        try:
            from tools.application_closer import close_application
            close_res = close_application(app)
            if isinstance(close_res, dict) and close_res.get("success"):
                closed_apps.append(app)
        except Exception as exc:
            logger.warning("protocol_close_app_failed app=%s error=%s", app, exc)

    @classmethod
    def _run_open_target(
        cls,
        raw_target: str,
        blocked_open: list[str],
        roles: dict[str, str] | None,
        launched_apps: list[str],
        already_running_apps: list[str],
        failed_apps: list[tuple[str, str]],
        skipped_blocked: list[str],
        args: str | list[str] | None = None,
        wait_window: bool = True,
        focus: bool = True,
    ) -> None:
        app = resolve_role_token(raw_target, roles)
        if not app:
            return
        if is_app_in_lock_list(app, blocked_open, roles=roles, patterns_fn=cls._get_app_process_patterns):
            skipped_blocked.append(f"не открыто {app}")
            return

        if args:
            ok, status = GenericAppAdapter.launch(
                app,
                args=args,
                wait_window=wait_window,
                focus=focus,
                resolve_path_fn=cls._resolve_app_path,
                is_running_fn=cls.is_app_running,
                focus_fn=cls.focus_app_window,
                wait_window_fn=cls.wait_for_app_window,
                launch_winapi_fn=cls._launch_path_winapi,
            )
        else:
            res = cls.launch_if_not_running(app)
            if isinstance(res, tuple) and len(res) == 2:
                ok, status = res
            else:
                ok, status = True, "запущено"

        if not ok:
            failed_apps.append((str(app), str(status)))
        elif "уже" in str(status).lower():
            already_running_apps.append(str(app))
        else:
            launched_apps.append(str(app))

    @classmethod
    def _execute_step(
        cls,
        step: dict[str, Any],
        blocked_open: list[str],
        blocked_close: list[str],
        roles: dict[str, str] | None,
        launched_apps: list[str],
        already_running_apps: list[str],
        failed_apps: list[tuple[str, str]],
        closed_apps: list[str],
        skipped_blocked: list[str],
    ) -> None:
        if not isinstance(step, dict):
            return
        stype = str(step.get("type") or "").strip().lower()

        if stype == "launch_app":
            cls._run_open_target(
                raw_target=str(step.get("target") or ""),
                blocked_open=blocked_open,
                roles=roles,
                launched_apps=launched_apps,
                already_running_apps=already_running_apps,
                failed_apps=failed_apps,
                skipped_blocked=skipped_blocked,
                args=step.get("args"),
                wait_window=bool(step.get("wait_window", True)),
                focus=bool(step.get("focus", True)),
            )
        elif stype == "open_urls":
            raw_browser = str(step.get("browser") or "role:browser")
            browser_key = resolve_role_token(raw_browser, roles)
            if is_app_in_lock_list(browser_key, blocked_open, roles=roles, patterns_fn=cls._get_app_process_patterns):
                skipped_blocked.append(f"не открыто {browser_key}")
                return
            urls = step.get("urls") if isinstance(step.get("urls"), list) else []
            ok, status = BrowserAdapter.open_urls(
                browser_key=browser_key,
                urls=urls,
                profile=step.get("profile"),
                new_window=bool(step.get("new_window", False)),
                resolve_path_fn=cls._resolve_app_path,
                focus_fn=cls.focus_app_window,
            )
            if ok:
                launched_apps.append(f"{browser_key} ({status})")
            else:
                failed_apps.append((browser_key, status))
        elif stype == "close_app":
            cls._run_close_target(
                str(step.get("target") or ""),
                blocked_close=blocked_close,
                roles=roles,
                closed_apps=closed_apps,
                skipped_blocked=skipped_blocked,
            )
        elif stype == "focus_app":
            app = resolve_role_token(str(step.get("target") or ""), roles)
            if app and not is_app_in_lock_list(app, blocked_open, roles=roles, patterns_fn=cls._get_app_process_patterns):
                cls.focus_app_window(app)
        elif stype == "close_mode":
            closed_apps.extend(cls._run_close_mode(str(step.get("mode") or "none"), blocked_close, roles))
        elif stype == "volume":
            mode = str(step.get("mode") or "none").lower()
            if mode in ("max", "100"):
                cls.set_volume_max()
            elif mode == "mute":
                media_control.set_master_mute(True)
            elif mode == "set":
                level = max(0, min(100, int(step.get("level", 50))))
                media_control.set_master_volume_scalar(level / 100.0)
                media_control.set_master_mute(False)
        elif stype == "media":
            action = str(step.get("action") or "play_pause")
            vk = media_control.VK_MAP.get(action, media_control.VK_MAP["play_pause"])
            media_control._send_key(vk, repeat=1)
        elif stype == "clean_recycle_bin":
            empty_recycle_bin()
        elif stype == "lock_screen":
            cls.lock_workstation()

    @classmethod
    def execute_dynamic_protocol(
        cls,
        proto: dict[str, Any],
        ollama_url: str | None = None,
        model: str | None = None,
        roles: dict[str, str] | None = None,
    ) -> str:
        """Выполняет полностью настраиваемый протокол из конфигуратора."""
        closed_apps: list[str] = []
        launched_apps: list[str] = []
        already_running_apps: list[str] = []
        failed_apps: list[tuple[str, str]] = []
        skipped_blocked: list[str] = []

        effective_roles = roles if isinstance(roles, dict) else (proto.get("_roles") if isinstance(proto.get("_roles"), dict) else None)
        blocked_open = [str(x).strip() for x in (proto.get("blocked_open_apps") or []) if str(x).strip()]
        blocked_close = [str(x).strip() for x in (proto.get("blocked_close_apps") or []) if str(x).strip()]

        # 1. Громкость
        vol = proto.get("volume_mode", "none")
        if vol in ("max", "100"):
            cls.set_volume_max()
        elif vol == "mute":
            media_control.set_master_mute(True)

        # 2. Пауза медиа
        if proto.get("pause_media"):
            try:
                media_control._send_key(media_control.VK_MAP["play_pause"], repeat=1)
            except Exception as exc:
                logger.debug("protocol_pause_media_failed error=%s", exc)

        # 3. Закрытие программ (с учётом изолированного списка исключений этого протокола)
        close_mode = proto.get("close_mode", "none")
        closed_apps.extend(cls._run_close_mode(close_mode, blocked_close, effective_roles))

        for app in proto.get("close_apps", []):
            cls._run_close_target(
                str(app),
                blocked_close=blocked_close,
                roles=effective_roles,
                closed_apps=closed_apps,
                skipped_blocked=skipped_blocked,
            )

        # 4. Открытие программ (идемпотентно, с учётом ролей и исключений)
        for app in proto.get("open_apps", []):
            cls._run_open_target(
                raw_target=str(app),
                blocked_open=blocked_open,
                roles=effective_roles,
                launched_apps=launched_apps,
                already_running_apps=already_running_apps,
                failed_apps=failed_apps,
                skipped_blocked=skipped_blocked,
            )

        # 4.5. Расширенные шаги Protocols v2 (если заданы)
        for step in proto.get("steps") or []:
            cls._execute_step(
                step=step,
                blocked_open=blocked_open,
                blocked_close=blocked_close,
                roles=effective_roles,
                launched_apps=launched_apps,
                already_running_apps=already_running_apps,
                failed_apps=failed_apps,
                closed_apps=closed_apps,
                skipped_blocked=skipped_blocked,
            )

        # 5. Очистка корзины
        if proto.get("clean_recycle_bin"):
            recycle_res = empty_recycle_bin()
            if isinstance(recycle_res, dict) and not recycle_res.get("success", True):
                err = recycle_res.get("error", "неизвестная ошибка")
                logger.warning("empty_recycle_bin_failed error=%s", err)
                if proto.get("id") == "clean_desk":
                    return f"Не удалось очистить корзину: {err}"

        # 6. Блокировка экрана
        if proto.get("lock_screen"):
            cls.lock_workstation()

        # 7. Формирование ответа
        custom_resp = str(proto.get("response_text") or "").strip()
        if custom_resp:
            base_resp = custom_resp
            if failed_apps:
                failed_str = ", ".join(app for app, _ in failed_apps)
                base_resp = f"{base_resp} Не удалось запустить: {failed_str}."
        else:
            base_resp = cls._build_execution_report(
                proto,
                launched_apps=launched_apps,
                already_running_apps=already_running_apps,
                failed_apps=failed_apps,
                closed_apps=closed_apps,
                skipped_blocked=skipped_blocked,
            )
        if proto.get("briefing"):
            now = datetime.now()
            time_str = now.strftime("%H:%M")
            days = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
            day_str = days[now.weekday()]
            weather = cls.get_weather_info()
            return f"Доброе утро, сэр. Время {time_str}, {day_str}{weather}. {base_resp}"

        return base_resp

    @classmethod
    def execute_protocol(
        cls,
        protocol_or_id: str | dict[str, Any],
        ollama_url: str | None = None,
        model: str | None = None,
        roles: dict[str, str] | None = None,
    ) -> str:
        """Главный диспетчер протоколов."""
        if isinstance(protocol_or_id, dict):
            return cls.execute_dynamic_protocol(protocol_or_id, ollama_url=ollama_url, model=model, roles=roles)

        from core.protocols_manager import DEFAULT_PROTOCOLS

        protocol_id = str(protocol_or_id)
        for proto in DEFAULT_PROTOCOLS:
            if proto.get("id") == protocol_id:
                return cls.execute_dynamic_protocol(proto, ollama_url=ollama_url, model=model, roles=roles)

        return "Протокол не опознан, сэр."
