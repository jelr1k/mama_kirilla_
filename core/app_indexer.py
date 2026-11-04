from __future__ import annotations

import logging
import os
from pathlib import Path
import re
import threading
import time
from typing import Any
import unicodedata

try:
    import winreg
except ImportError:  # pragma: no cover
    winreg = None  # type: ignore

try:
    import win32com.client
except ImportError:  # pragma: no cover
    win32com = None  # type: ignore

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover
    fuzz = None  # type: ignore

from core.alias_manager import AUTO_RUSSIAN_ALIASES, EXTRA_RUSSIAN_ALIASES

logger = logging.getLogger("jarvis.app_indexer")

# Черный список слов в названии ярлыков для исключения служебных утилит
_IGNORED_STEM_KEYWORDS = {
    "uninstall", "деинсталлировать", "удалить", "удаление",
    "help", "справка", "manual", "руководство", "readme",
    "documentation", "документация", "release notes", "changelog",
    "website", "веб-сайт", "visit", "url", "license", "лицензия",
    "configure", "configuration", "settings", "настройка", "updater",
    "update", "crash reporter", "feedback",
}

_WINDOWS_START_MENU_DIRS = [
    Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
    Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
]


def _normalize_name(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold().replace("ё", "е")
    text = re.sub(r"[\W_]+", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


def _resolve_shortcut_target(path: Path) -> Path | None:
    if path.suffix.lower() != ".lnk":
        return path if path.suffix.lower() == ".exe" else None
    if win32com is None:
        return None
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(str(path))
        target = (shortcut.TargetPath or "").strip()
        if not target:
            return None
        target_path = Path(target)
        if target_path.suffix.lower() == ".exe" and target_path.exists():
            return target_path.resolve()
        return None
    except Exception:
        logger.debug("app_indexer_resolve_shortcut_failed path=%s", path)
        return None


class AppIndexer:
    """Безопасный сканер и резолвер установленного софта Windows.

    Индексирует приложения из Start Menu и системного реестра App Paths,
    привязывает русскоязычные алиасы и предоставляет мгновенный запуск.
    """

    _instance: AppIndexer | None = None

    def __init__(self, event_bus: Any = None, custom_start_dirs: list[Path] | None = None):
        self.event_bus = event_bus
        self._custom_start_dirs = custom_start_dirs
        self._cached_apps: list[dict[str, Any]] = []
        self._last_scan_time: float = 0.0
        self._scan_ttl: float = 120.0  # Кэш на 2 минуты
        self._lock = threading.Lock()
        AppIndexer._instance = self

    @classmethod
    def get_instance(cls, event_bus: Any = None) -> AppIndexer:
        if cls._instance is None:
            cls._instance = AppIndexer(event_bus=event_bus)
        return cls._instance

    def _generate_aliases(self, app_name: str, exe_stem: str) -> list[str]:
        """Генерирует русские и альтернативные фразы для голосового вызова."""
        aliases: set[str] = set()
        clean_name = _normalize_name(app_name)
        clean_stem = _normalize_name(exe_stem)

        if clean_name:
            aliases.add(clean_name)
        if clean_stem:
            aliases.add(clean_stem)

        # 1. Поиск в словарях известных русских алиасов
        for base_key in (clean_name, clean_stem, app_name.lower(), exe_stem.lower()):
            if base_key in AUTO_RUSSIAN_ALIASES:
                aliases.add(AUTO_RUSSIAN_ALIASES[base_key])
            if base_key in EXTRA_RUSSIAN_ALIASES:
                for alias in EXTRA_RUSSIAN_ALIASES[base_key]:
                    aliases.add(alias)

        # 2. Простая транслитерация частых английских сочетаний
        translit_map = {
            "discord": "дискорд",
            "telegram": "телеграм",
            "steam": "стим",
            "obs": "обс",
            "spotify": "спотифай",
            "chrome": "хром",
            "firefox": "файрфокс",
            "opera": "опера",
            "code": "код",
            "blender": "блендер",
            "notepad": "блокнот",
            "calculator": "калькулятор",
        }
        for eng, rus in translit_map.items():
            if eng in clean_name or eng in clean_stem:
                aliases.add(rus)

        return sorted(a for a in aliases if a)

    def scan_installed_apps(self, force: bool = False) -> list[dict[str, Any]]:
        """Сканирует программы в Start Menu и реестре Windows."""
        with self._lock:
            now = time.time()
            if not force and self._cached_apps and (now - self._last_scan_time) < self._scan_ttl:
                return list(self._cached_apps)

            apps_by_exe: dict[str, dict[str, Any]] = {}
            start_dirs = self._custom_start_dirs if self._custom_start_dirs is not None else _WINDOWS_START_MENU_DIRS

            # 1. Сканирование меню «Пуск» (.lnk)
            for root_dir in start_dirs:
                if not root_dir.exists():
                    continue
                try:
                    for lnk_file in root_dir.rglob("*.lnk"):
                        stem_lower = lnk_file.stem.lower()
                        # Исключаем деинсталляторы и служебные ярлыки
                        if any(kw in stem_lower for kw in _IGNORED_STEM_KEYWORDS):
                            continue

                        target_exe = _resolve_shortcut_target(lnk_file)
                        exe_str = str(target_exe.resolve()).lower() if target_exe else None
                        app_name = lnk_file.stem

                        # Если ярлык указывает на реальный exe
                        if exe_str and exe_str.endswith(".exe"):
                            if exe_str not in apps_by_exe:
                                exe_path = Path(exe_str)
                                aliases = self._generate_aliases(app_name, exe_path.stem)
                                apps_by_exe[exe_str] = {
                                    "id": f"app_{len(apps_by_exe) + 1}",
                                    "name": app_name,
                                    "executable": exe_str,
                                    "shortcut": str(lnk_file.resolve()),
                                    "aliases": aliases,
                                    "source": "start_menu",
                                }
                        elif not exe_str:
                            # Даже если не удалось резолвить через win32com, сохраняем ярлык
                            key = str(lnk_file.resolve()).lower()
                            if key not in apps_by_exe:
                                aliases = self._generate_aliases(app_name, lnk_file.stem)
                                apps_by_exe[key] = {
                                    "id": f"app_{len(apps_by_exe) + 1}",
                                    "name": app_name,
                                    "executable": None,
                                    "shortcut": str(lnk_file.resolve()),
                                    "aliases": aliases,
                                    "source": "start_menu",
                                }
                except Exception as exc:
                    logger.debug("app_indexer_scan_start_menu_error root=%s err=%s", root_dir, exc)

            # 2. Сканирование реестра: App Paths
            if winreg is not None:
                for hkey in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                    sub_key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"
                    try:
                        with winreg.OpenKey(hkey, sub_key_path) as root_key:
                            num_subkeys = winreg.QueryInfoKey(root_key)[0]
                            for i in range(num_subkeys):
                                try:
                                    app_key_name = winreg.EnumKey(root_key, i)
                                    with winreg.OpenKey(root_key, app_key_name) as app_key:
                                        exe_path_raw, _ = winreg.QueryValueEx(app_key, "")
                                        if not exe_path_raw:
                                            continue
                                        exe_path_clean = str(exe_path_raw).strip('"')
                                        p = Path(exe_path_clean)
                                        if p.suffix.lower() == ".exe" and p.exists():
                                            exe_norm = str(p.resolve()).lower()
                                            if exe_norm not in apps_by_exe:
                                                name = p.stem.replace("_", " ").title()
                                                aliases = self._generate_aliases(name, p.stem)
                                                apps_by_exe[exe_norm] = {
                                                    "id": f"app_{len(apps_by_exe) + 1}",
                                                    "name": name,
                                                    "executable": str(p.resolve()),
                                                    "shortcut": None,
                                                    "aliases": aliases,
                                                    "source": "registry",
                                                }
                                except (OSError, ValueError):
                                    continue
                    except (OSError, ValueError):
                        continue

            results = sorted(apps_by_exe.values(), key=lambda x: x["name"].lower())
            self._cached_apps = results
            self._last_scan_time = now
            logger.info("app_indexer_scanned_apps total=%d", len(results))
            return list(results)

    def resolve_app(self, query: str) -> dict[str, Any] | None:
        """Находит установленное приложение по названию, алиасу или нечёткому совпадению."""
        if not query or not query.strip():
            return None

        q_norm = _normalize_name(query)
        apps = self.scan_installed_apps()

        # 1. Точное совпадение по алиасам или имени
        for app in apps:
            if _normalize_name(app["name"]) == q_norm:
                return app
            exe_stem = Path(app["executable"]).stem if app.get("executable") else ""
            if _normalize_name(exe_stem) == q_norm:
                return app
            for alias in app.get("aliases", []):
                if _normalize_name(alias) == q_norm:
                    return app

        # 2. Нечёткий поиск (fuzzy matching)
        if fuzz is not None:
            best_match: dict[str, Any] | None = None
            best_score = 0
            for app in apps:
                # Сравниваем с именем приложения
                score = fuzz.WRatio(q_norm, _normalize_name(app["name"]))
                if score > best_score:
                    best_score = score
                    best_match = app

                # Сравниваем со всеми алиасами приложения
                for alias in app.get("aliases", []):
                    alias_score = fuzz.WRatio(q_norm, _normalize_name(alias))
                    if alias_score > best_score:
                        best_score = alias_score
                        best_match = app

            if best_match and best_score >= 82:
                logger.info("app_indexer_fuzzy_match query=%r matched=%r score=%d", query, best_match["name"], best_score)
                return best_match

        return None

    def launch_app(self, target: str | dict[str, Any]) -> dict[str, Any]:
        """Запускает приложение по объекту приложения, имени или пути."""
        app_obj: dict[str, Any] | None = None
        if isinstance(target, dict):
            app_obj = target
        else:
            app_obj = self.resolve_app(target)
            if not app_obj:
                # Проверяем, может передан путь к известному проиндексированному объекту
                apps = self.scan_installed_apps()
                for item in apps:
                    if item.get("shortcut") == target or item.get("executable") == target:
                        app_obj = item
                        break

        if not app_obj:
            return {"success": False, "error": f"Приложение «{target}» не найдено на ПК."}

        target_path = app_obj.get("shortcut") or app_obj.get("executable")
        if not target_path or not Path(target_path).exists():
            return {"success": False, "error": f"Файл приложения недоступен: {target_path}"}

        try:
            os.startfile(target_path)
            logger.info("app_indexer_launched_success app=%r path=%s", app_obj.get("name"), target_path)
            return {"success": True, "app": app_obj.get("name"), "path": target_path}
        except Exception as exc:
            logger.exception("app_indexer_launch_failed app=%r path=%s", app_obj.get("name"), target_path)
            return {"success": False, "error": f"Ошибка запуска {app_obj.get('name')}: {exc}"}
