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
            "obs": ["obs64.exe", "obs32.exe", "obs.exe"],
            "telegram": ["telegram.exe"],
            "spotify": ["spotify.exe"],
            "chrome": ["chrome.exe"],
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
            # Попробовать запустить напрямую через shell/startfile если это зарегистрированная программа
            try:
                os.startfile(app_key)
                return True, "запущено"
            except Exception:
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
        target_p = Path(app_key).expanduser()
        if target_p.exists():
            return target_p

        key = app_key.lower().strip()

        # 1. Opera
        if key in ("opera", "опера", "opera gx"):
            candidates = [
                Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Браузер Opera GX.lnk",
                Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Opera GX" / "opera.exe",
                Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Opera" / "opera.exe",
            ]
            for c in candidates:
                if c.exists():
                    return c

        # 2. Discord
        if key in ("discord", "дискорд"):
            candidates = [
                Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Discord Inc" / "Discord.lnk",
                Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Discord.lnk",
                Path(os.environ.get("LOCALAPPDATA", "")) / "Discord" / "Update.exe",
            ]
            for c in candidates:
                if c.exists():
                    return c

        # 3. Steam
        if key in ("steam", "стим"):
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
                    val, _ = winreg.QueryValueEx(k, "SteamExe")
                    sp = Path(val)
                    if sp.exists():
                        return sp
            except Exception:
                pass
            fallback = Path("D:/rzz/steam/steam.exe")
            if fallback.exists():
                return fallback

        # 4. Antigravity
        if key in ("antigravity", "антигравити"):
            ag_exe = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "antigravity" / "Antigravity.exe"
            if ag_exe.exists():
                return ag_exe
            lnk = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Antigravity.lnk"
            if lnk.exists():
                return lnk

        # 5. Antigravity Unlocker
        if key in ("unlocker", "анлокер", "антигравити анлокер"):
            downloads = Path(os.environ.get("USERPROFILE", "")) / "Downloads"
            if downloads.is_dir():
                for p in sorted(downloads.glob("AG_*.exe"), reverse=True):
                    if p.is_file():
                        return p

        # 6. Общий поиск через find_application
        try:
            from tools.applications import find_application
            found = find_application(app_key)
            if found.get("success") and found.get("path"):
                p = Path(found["path"])
                if p.exists():
                    return p
        except Exception:
            pass

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
    def _try_generate_llm_response(cls, proto: dict[str, Any], ollama_url: str | None = None, model: str | None = None) -> str | None:
        """Попытка быстро сгенерировать ответ через Ollama, если модель уже загружена в память."""
        base_url = (ollama_url or "http://localhost:11434").rstrip("/")
        name = proto.get("name") or "Сценарий"

        # Проверяем, есть ли готовые запущенные модели в Ollama (/api/ps)
        try:
            req_ps = urllib.request.Request(f"{base_url}/api/ps", method="GET")
            with urllib.request.urlopen(req_ps, timeout=0.8) as resp:
                if resp.status != 200:
                    return None
                data = json.loads(resp.read().decode("utf-8"))
                loaded_models = [m.get("name", "") for m in data.get("models", [])]
                if not loaded_models:
                    return None
                active_model = model if (model and any(model in lm for lm in loaded_models)) else loaded_models[0]
        except Exception:
            return None

        # Формируем краткий контекст действий
        actions = []
        if proto.get("open_apps"):
            actions.append("открыл " + ", ".join(proto["open_apps"]))
        if proto.get("close_mode") == "steam_games":
            actions.append("закрыл игры Steam")
        elif proto.get("close_mode") == "cinema":
            actions.append("закрыл лишние программы под кино")
        elif proto.get("close_mode") == "game":
            actions.append("закрыл фоновые программы под игры")
        elif proto.get("close_apps"):
            actions.append("закрыл " + ", ".join(proto["close_apps"]))
        if proto.get("volume_mode") == "max":
            actions.append("звук на 100%")
        elif proto.get("volume_mode") == "mute":
            actions.append("выключил звук")
        if proto.get("pause_media"):
            actions.append("поставил медиа на паузу")
        if proto.get("clean_recycle_bin"):
            actions.append("очистил корзину")
        if proto.get("lock_screen"):
            actions.append("заблокировал экран")

        action_summary = "; ".join(actions) if actions else "все директивы выполнены"

        payload = json.dumps({
            "model": active_model,
            "messages": [
                {
                    "role": "system",
                    "content": "Ты — JARVIS, саркастичный и преданный ИИ Тони Старка. Отвечай ровно одним кратким предложением (до 15 слов). Без кавычек, без смайлов, без скобок."
                },
                {
                    "role": "user",
                    "content": f"Ты только что активировал протокол «{name}». Выполнено: {action_summary}. Доложи об этом Тони Старку."
                }
            ],
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 40
            }
        }).encode("utf-8")

        try:
            req_chat = urllib.request.Request(
                f"{base_url}/api/chat",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req_chat, timeout=2.5) as resp:
                if resp.status == 200:
                    res_json = json.loads(resp.read().decode("utf-8"))
                    text = res_json.get("message", {}).get("content", "").strip()
                    text = text.strip("\"'«»\n\r")
                    if text:
                        logger.info("protocol_llm_response_generated text=%r", text)
                        return text
        except Exception as exc:
            logger.debug("protocol_llm_fallback_triggered exc=%s", exc)

        return None

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
        """Гибридный выбор ответа: LLM при быстрой готовности или мгновенный Stark-генератор."""
        resp = cls._try_generate_llm_response(proto, ollama_url=ollama_url, model=model)
        if resp:
            return resp
        return cls._generate_stark_fallback(proto)

    @classmethod
    def execute_dynamic_protocol(cls, proto: dict[str, Any], ollama_url: str | None = None, model: str | None = None) -> str:
        """Выполняет полностью настраиваемый протокол из конфигуратора."""
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
            except Exception:
                pass

        # 3. Закрытие программ
        close_mode = proto.get("close_mode", "none")
        if close_mode == "steam_games":
            cls.close_steam_games()
        elif close_mode == "cinema":
            cls.close_apps_for_cinema()
        elif close_mode == "game":
            cls.close_user_apps_for_gaming()

        for app in proto.get("close_apps", []):
            try:
                from tools.applications import close_application
                close_application(app)
            except Exception:
                pass

        # 4. Открытие программ (идемпотентно!)
        for app in proto.get("open_apps", []):
            cls.launch_if_not_running(app)

        # 5. Очистка корзины
        if proto.get("clean_recycle_bin"):
            empty_recycle_bin()

        # 6. Блокировка экрана
        if proto.get("lock_screen"):
            cls.lock_workstation()

        # 7. Формирование ответа
        custom_resp = str(proto.get("response_text") or "").strip()
        if custom_resp:
            base_resp = custom_resp
        else:
            base_resp = cls.generate_dynamic_response(proto, ollama_url=ollama_url, model=model)
        if proto.get("briefing"):
            now = datetime.now()
            time_str = now.strftime("%H:%M")
            days = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
            day_str = days[now.weekday()]
            weather = cls.get_weather_info()
            return f"Доброе утро, сэр. Время {time_str}, {day_str}{weather}. {base_resp}"

        return base_resp

    @classmethod
    def execute_protocol(cls, protocol_or_id: str | dict[str, Any], ollama_url: str | None = None, model: str | None = None) -> str:
        """Главный диспетчер протоколов."""
        if isinstance(protocol_or_id, dict):
            return cls.execute_dynamic_protocol(protocol_or_id, ollama_url=ollama_url, model=model)

        protocol_id = str(protocol_or_id)
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
            cls.close_steam_games()
            cls.launch_if_not_running("opera")
            cls.launch_if_not_running("antigravity")
            cls.launch_if_not_running("unlocker")
            return "Протокол «Работа» активирован, сэр. Игра закрыта, рабочие инструменты Opera, Antigravity и Unlocker готовы. Discord активен."

        elif protocol_id == "default":
            cls.set_volume_max()
            return "Стандартный режим восстановлен, сэр. Громкость на 100%, все системы в исходном состоянии."

        return "Протокол не опознан, сэр."
