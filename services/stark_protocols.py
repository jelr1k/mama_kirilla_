from __future__ import annotations

import ctypes
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import time
import urllib.request

import psutil

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
    def is_app_running(cls, app_key: str) -> bool:
        """Проверяет, запущен ли процесс приложения (без регистра и с поддержкой вариантов)."""
        app_key = app_key.lower().strip()
        name_map = {
            "opera": ["opera.exe"],
            "discord": ["discord.exe"],
            "steam": ["steam.exe"],
            "antigravity": ["antigravity.exe"],
            "unlocker": ["ag_2.", "unlocker"],
        }
        target_patterns = name_map.get(app_key, [f"{app_key}.exe", app_key])

        for proc in psutil.process_iter(["name"]):
            try:
                pname = (proc.info.get("name") or "").lower()
                for pat in target_patterns:
                    if pat.endswith(".exe"):
                        if pname == pat:
                            return True
                    elif pat in pname:
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    @classmethod
    def launch_if_not_running(cls, app_key: str) -> tuple[bool, str]:
        """Запускает приложение, ТОЛЬКО если оно ещё не запущено (идемпотентность)."""
        if cls.is_app_running(app_key):
            logger.info("app_already_running key=%s", app_key)
            return True, "уже запущено"

        path = cls._resolve_app_path(app_key)
        if not path or not path.exists():
            logger.warning("app_path_not_found key=%s path=%s", app_key, path)
            return False, "путь не найден"

        try:
            logger.info("launching_app key=%s path=%s", app_key, path)
            os.startfile(str(path))
            return True, "запущено"
        except Exception as exc:
            logger.exception("launch_app_error key=%s path=%s", app_key, path)
            return False, str(exc)

    @classmethod
    def _resolve_app_path(cls, app_key: str) -> Path | None:
        """Находит исполняемый файл или ярлык приложения на диске."""
        app_key = app_key.lower().strip()

        # 1. Opera
        if app_key == "opera":
            candidates = [
                Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Браузер Opera GX.lnk",
                Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Opera GX" / "opera.exe",
                Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Opera" / "opera.exe",
            ]
            for c in candidates:
                if c.exists():
                    return c

        # 2. Discord
        if app_key == "discord":
            candidates = [
                Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Discord Inc" / "Discord.lnk",
                Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Discord.lnk",
                Path(os.environ.get("LOCALAPPDATA", "")) / "Discord" / "Update.exe",
            ]
            for c in candidates:
                if c.exists():
                    return c

        # 3. Steam
        if app_key == "steam":
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
                    val, _ = winreg.QueryValueEx(key, "SteamExe")
                    sp = Path(val)
                    if sp.exists():
                        return sp
            except Exception:
                pass
            fallback = Path("D:/rzz/steam/steam.exe")
            if fallback.exists():
                return fallback

        # 4. Antigravity
        if app_key == "antigravity":
            ag_exe = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "antigravity" / "Antigravity.exe"
            if ag_exe.exists():
                return ag_exe
            lnk = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Antigravity.lnk"
            if lnk.exists():
                return lnk

        # 5. Antigravity Unlocker
        if app_key == "unlocker":
            downloads = Path(os.environ.get("USERPROFILE", "")) / "Downloads"
            if downloads.is_dir():
                for p in sorted(downloads.glob("AG_*.exe"), reverse=True):
                    if p.is_file():
                        return p

        return None

    @classmethod
    def close_steam_games(cls) -> list[str]:
        """Закрывает только запущенные игры Steam (не закрывая сам Steam и Wallpaper Engine)."""
        closed = []
        for proc in psutil.process_iter(["pid", "name", "exe", "cwd"]):
            try:
                name = (proc.info.get("name") or "").lower()
                if name in cls.PROTECTED_STEAM_TOOLS or name in cls.PROTECTED_PROCESS_NAMES:
                    continue

                exe = (proc.info.get("exe") or "").lower()
                cwd = (proc.info.get("cwd") or "").lower()
                if "steamapps" in exe or "steamapps" in cwd:
                    proc.terminate()
                    closed.append(proc.info.get("name"))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return closed

    @classmethod
    def close_user_apps_for_gaming(cls) -> list[str]:
        """Закрывает Opera и прочие фоновые программы перед игрой (Steam и Discord остаются!)."""
        closed = []
        allowed = {
            "steam.exe", "steamwebhelper.exe", "discord.exe",
            "wallpaper32.exe", "wallpaper64.exe", "winrtutil64.exe", "webwallpaper32.exe",
        }
        targets_to_close = {
            "opera.exe", "chrome.exe", "msedge.exe", "firefox.exe",
            "antigravity.exe", "telegram.exe", "spotify.exe",
        }

        for proc in psutil.process_iter(["pid", "name"]):
            try:
                name = (proc.info.get("name") or "").lower()
                if name in allowed or name in cls.PROTECTED_PROCESS_NAMES:
                    continue

                if name in targets_to_close or name.startswith("ag_2."):
                    proc.terminate()
                    closed.append(name)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return closed

    @classmethod
    def close_apps_for_cinema(cls) -> list[str]:
        """Закрывает предыдущее состояние, оставляя Discord, Steam и Opera."""
        closed = []
        allowed = {
            "steam.exe", "steamwebhelper.exe", "discord.exe", "opera.exe",
            "wallpaper32.exe", "wallpaper64.exe", "winrtutil64.exe", "webwallpaper32.exe",
        }
        targets_to_close = {
            "antigravity.exe", "chrome.exe", "firefox.exe",
        }

        # Закрываем также игры из Steam
        closed.extend(cls.close_steam_games())

        for proc in psutil.process_iter(["pid", "name"]):
            try:
                name = (proc.info.get("name") or "").lower()
                if name in allowed or name in cls.PROTECTED_PROCESS_NAMES:
                    continue

                if name in targets_to_close or name.startswith("ag_2."):
                    proc.terminate()
                    closed.append(name)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
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
        except Exception:
            pass
        try:
            ctypes.windll.user32.LockWorkStation()
        except Exception as exc:
            logger.exception("LockWorkStation error: %s", exc)

    @classmethod
    def get_weather_info(cls) -> str:
        """Легкий опрос погоды с жестким таймаутом (чтобы не вешать систему)."""
        try:
            url = "https://api.open-meteo.com/v1/forecast?latitude=55.7558&longitude=37.6173&current_weather=true"
            req = urllib.request.Request(url, headers={"User-Agent": "Jarvis/1.0"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                temp = data.get("current_weather", {}).get("temperature")
                if temp is not None:
                    return f", в Москве сейчас {round(temp)}°"
        except Exception:
            pass
        return ""

    @classmethod
    def execute_protocol(cls, protocol_id: str) -> str:
        """Главный диспетчер протоколов."""
        now = datetime.now()
        time_str = now.strftime("%H:%M")
        days = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
        day_str = days[now.weekday()]

        if protocol_id == "morning":
            cls.set_volume_max()
            cls.launch_if_not_running("opera")
            cls.launch_if_not_running("discord")
            cls.launch_if_not_running("steam")
            weather = cls.get_weather_info()
            return f"Доброе утро, сэр. Время {time_str}, {day_str}{weather}. Громкость на максимуме. Браузер, Discord и Steam запущены. Все системы готовы к работе."

        elif protocol_id == "lockdown":
            cls.lock_workstation()
            return "Блокирую терминал. До вашего возвращения, сэр."

        elif protocol_id == "cinema":
            cls.set_volume_max()
            cls.launch_if_not_running("opera")
            cls.close_apps_for_cinema()
            return "Протокол «Кино» активирован, сэр. Громкость на 100%, браузер открыт. Discord и Steam сохранены. Приятного просмотра."

        elif protocol_id == "game":
            cls.launch_if_not_running("discord")
            cls.launch_if_not_running("steam")
            cls.close_user_apps_for_gaming()
            return "Игровой протокол активирован, сэр. Выделяю ресурсы: браузер и программы закрыты. Steam и Discord на связи. Приятной игры."

        elif protocol_id == "clean_desk":
            res = empty_recycle_bin()
            if res.get("success"):
                return "Корзина очищена, сэр. Рабочее пространство в полном порядке."
            return f"Не удалось очистить корзину: {res.get('error', 'неизвестная ошибка')}"

        elif protocol_id == "work":
            # Закрываем запущенную игру из Steam
            cls.close_steam_games()
            # Открываем Оперу, Антигравити, Анлокер
            cls.launch_if_not_running("opera")
            cls.launch_if_not_running("antigravity")
            cls.launch_if_not_running("unlocker")
            # Discord не трогаем
            return "Протокол «Работа» активирован, сэр. Игра закрыта, рабочие инструменты Opera, Antigravity и Unlocker готовы. Discord активен."

        elif protocol_id == "default":
            cls.set_volume_max()
            return "Стандартный режим восстановлен, сэр. Громкость на 100%, все системы в исходном состоянии."

        return "Протокол не опознан, сэр."
