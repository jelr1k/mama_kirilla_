from __future__ import annotations

import json
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
    import pythoncom
except ImportError:  # pragma: no cover
    pythoncom = None  # type: ignore

try:
    import win32com.client
except ImportError:  # pragma: no cover
    win32com = None  # type: ignore

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover
    fuzz = None  # type: ignore

from core.alias_manager import AUTO_RUSSIAN_ALIASES, EXTRA_RUSSIAN_ALIASES
from core.app_paths import HIDDEN_APPS_FILE, INSTALLED_APPS_FILE, ensure_application_dirs

logger = logging.getLogger("jarvis.app_indexer")

# Черный список слов в названии ярлыков/бинарников для исключения служебного мусора
_IGNORED_STEM_KEYWORDS = {
    "uninstall", "unins", "uninstaller", "деинсталлировать", "удалить", "удаление",
    "help", "справка", "manual", "руководство", "readme",
    "documentation", "документация", "release notes", "changelog",
    "website", "веб-сайт", "visit", "url", "license", "лицензия",
    "configure", "configuration", "settings", "настройка", "updater",
    "update", "crash reporter", "crashpad", "bugsplat", "feedback", "bug report",
    "redist", "vcredist", "directx", "physx", "setup", "installer", "install manager",
    "repair", "diagnostic", "diagnostics", "troubleshoot",
    "command prompt", "командная строка", "powershell", "regedit",
    "редактор реестра", "registry editor", "сведения о системе", "system information",
    "просмотр событий", "event viewer", "монитор ресурсов", "resource monitor",
    "планировщик заданий", "task scheduler", "управление компьютером", "computer management",
    "очистка диска", "disk cleanup", "дефрагментация", "dfrgui",
    "component services", "administrative tools", "recoverydrive",
    "экранный диктор", "экранная клавиатура", "таблица символов", "character map",
    "steps recorder", "wordpad", "module docs", "idle (", "python 3.",
    "about java", "application verifier", "package manager", "control panel",
    "remote desktop", "overlay host", "speed test", "proxy generator",
    "control panels", "fairlight studio utility", "localization reference",
    "skin format reference", "samples", "sample ", "telemetry",
}

# Базовые системные утилиты Windows, которые полезно оставлять в каталоге
_ALLOWED_SYSTEM_EXES = {
    "notepad.exe",
    "calc.exe",
    "mspaint.exe",
    "taskmgr.exe",
    "snippingtool.exe",
    "explorer.exe",
}

_ALLOWED_SYSTEM_NAMES = {
    "notepad", "блокнот",
    "calculator", "калькулятор",
    "paint", "mspaint",
    "task manager", "диспетчер задач",
    "snipping tool", "snippingtool", "ножницы",
    "file explorer", "проводник",
}

# Мусорные подпапки меню «Пуск», откуда служебные ярлыки не должны попадать в предложения
_IGNORED_SHORTCUT_DIR_MARKERS = (
    "\\administrative tools\\",
    "\\администрирование\\",
    "\\windows kits\\",
    "\\visual studio tools\\",
    "\\sdk\\",
    "\\system tools\\",
    "\\accessibility\\",
    "\\специальные возможности\\",
    "\\startup\\",
    "\\автозагрузка\\",
    "\\maintenance\\",
)

# Системные каталоги Windows/SDK, откуда все прочее отсеивается как мусор
_SYSTEM_PATH_MARKERS = (
    "\\windows\\system32\\",
    "\\windows\\syswow64\\",
    "\\windows\\winsxs\\",
    "\\windows\\servicing\\",
    "\\windows\\microsoft.net\\",
    "\\windows\\immersivecontrolpanel\\",
    "\\windows\\systemapps\\",
    "\\windows kits\\",
    "\\common files\\microsoft shared\\",
    "\\microsoft visual studio\\installer\\",
)

# Приоритетные категории для динамических предложений в протоколах
_CATEGORY_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("browser", ("vivaldi", "opera", "chrome", "firefox", "msedge", "edge", "brave", "yandex", "arc", "zen", "librewolf", "waterfox", "tor")),
    ("messenger", ("discord", "telegram", "teamspeak", "slack", "element", "viber", "whatsapp", "skype")),
    ("gaming", ("steam", "epicgameslauncher", "epic games", "gog galaxy", "battle.net", "ubisoft", "ea app", "riot", "minecraft", "prismlauncher", "modrinth")),
    ("media", ("spotify", "vlc", "mpc-hc", "potplayer", "yandex music", "яндекс музыка", "aimp", "foobar2000")),
    ("streaming", ("obs", "streamlabs", "nvidia broadcast")),
    ("work", ("code", "visual studio", "antigravity", "cursor", "pycharm", "idea", "webstorm", "blender", "figma", "photoshop", "obsidian", "notion", "notepad++", "sublime")),
    ("utility", ("unlocker", "zapret", "happ", "flclash", "amnezia", "qbittorrent", "notepad", "calc", "7-zip", "winrar")),
]

_GENERIC_EXE_STEMS = {"launcher", "client", "app", "start", "main", "bin", "run", "bootstrap"}

_WINDOWS_START_MENU_DIRS = [
    Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
    Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
]


def _normalize_name(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold().replace("ё", "е")
    text = re.sub(r"[\W_]+", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


def _is_system_or_junk(app_name: str, exe_path: str | None, shortcut_path: str | None = None) -> bool:
    """Отсекает системный мусор Windows и служебные бинарники, оставляя базовые утилиты."""
    name_low = (app_name or "").strip().lower()
    if name_low in _ALLOWED_SYSTEM_NAMES:
        return False

    if exe_path:
        exe_low = exe_path.replace("/", "\\").lower()
        exe_name = Path(exe_low).name
        if exe_name in _ALLOWED_SYSTEM_EXES:
            return False

    if any(kw in name_low for kw in _IGNORED_STEM_KEYWORDS):
        return True

    if shortcut_path:
        lnk_low = shortcut_path.replace("/", "\\").lower()
        if any(marker in lnk_low for marker in _IGNORED_SHORTCUT_DIR_MARKERS):
            return True

    if exe_path:
        exe_low = exe_path.replace("/", "\\").lower()
        exe_stem = Path(exe_low).stem

        if any(kw in exe_stem for kw in _IGNORED_STEM_KEYWORDS):
            return True

        if any(marker in exe_low for marker in _SYSTEM_PATH_MARKERS):
            return True

    return False


def _classify_app(app_name: str, exe_stem: str) -> str:
    """Определяет категорию приложения для сортировки предложений."""
    haystack = f"{_normalize_name(app_name)} {_normalize_name(exe_stem)}"
    for category, keywords in _CATEGORY_KEYWORDS:
        for kw in keywords:
            if re.search(rf"(?<!\w){re.escape(kw)}(?!\w)", haystack):
                return category
    return "app"


def _suggest_key(app: dict[str, Any]) -> str:
    """Формирует компактный ключ приложения для open_apps/close_apps."""
    exe = app.get("executable")
    if exe:
        stem = Path(exe).stem.lower()
        if stem and stem not in _GENERIC_EXE_STEMS and len(stem) >= 2:
            return stem
    return str(app.get("name") or "").strip().lower()


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

    def __init__(
        self,
        event_bus: Any = None,
        custom_start_dirs: list[Path] | None = None,
        cache_file: Path | None = None,
        hidden_file: Path | None = None,
    ):
        self.event_bus = event_bus
        self._custom_start_dirs = custom_start_dirs
        if cache_file is not None:
            self._cache_file: Path | None = cache_file
        elif custom_start_dirs is None:
            self._cache_file = INSTALLED_APPS_FILE
        else:
            self._cache_file = None

        if hidden_file is not None:
            self._hidden_file: Path | None = hidden_file
        elif custom_start_dirs is None:
            self._hidden_file = HIDDEN_APPS_FILE
        else:
            self._hidden_file = None

        self._cached_apps: list[dict[str, Any]] = []
        self._hidden_apps: set[str] = set()
        self._last_scan_time: float = 0.0
        self._scan_ttl: float = 120.0  # Кэш на 2 минуты
        self._lock = threading.RLock()
        self._load_hidden_apps()
        self._load_cache()
        AppIndexer._instance = self

    def _load_hidden_apps(self) -> None:
        """Загружает список скрытых пользователем приложений."""
        if not self._hidden_file or not self._hidden_file.is_file():
            return
        try:
            with open(self._hidden_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
            items = raw.get("hidden", []) if isinstance(raw, dict) else raw
            if isinstance(items, list):
                self._hidden_apps = {
                    _normalize_name(str(x)) for x in items if _normalize_name(str(x))
                }
        except Exception as exc:
            logger.debug("app_indexer_hidden_load_failed path=%s err=%s", self._hidden_file, exc)

    def _save_hidden_apps(self) -> None:
        """Сохраняет список скрытых приложений на диск."""
        if not self._hidden_file:
            return
        try:
            ensure_application_dirs()
            self._hidden_file.parent.mkdir(parents=True, exist_ok=True)
            payload = {"hidden": sorted(self._hidden_apps)}
            tmp_path = self._hidden_file.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            tmp_path.replace(self._hidden_file)
        except Exception as exc:
            logger.debug("app_indexer_hidden_save_failed path=%s err=%s", self._hidden_file, exc)

    @staticmethod
    def _app_hidden_tokens(app: dict[str, Any]) -> set[str]:
        tokens: set[str] = set()
        name = str(app.get("name") or "").strip()
        if name:
            tokens.add(_normalize_name(name))
        key = _suggest_key(app)
        if key:
            tokens.add(_normalize_name(key))
        exe = app.get("executable")
        if exe:
            tokens.add(_normalize_name(Path(str(exe)).stem))
        tokens.discard("")
        return tokens

    def is_app_hidden(self, app: dict[str, Any]) -> bool:
        """Проверяет, скрыл ли пользователь приложение из предложений."""
        with self._lock:
            if not self._hidden_apps:
                return False
            return bool(self._app_hidden_tokens(app) & self._hidden_apps)

    def get_hidden_apps(self) -> list[str]:
        with self._lock:
            return sorted(self._hidden_apps)

    def set_app_hidden(self, app_key: str, hidden: bool) -> list[str]:
        """Скрывает или возвращает приложение в выдачу по его ключу или имени."""
        norm = _normalize_name(app_key)
        if not norm:
            return self.get_hidden_apps()

        with self._lock:
            # Находим все токены приложения, если оно есть в кэше
            target_tokens = {norm}
            for app in self._cached_apps:
                tokens = self._app_hidden_tokens(app)
                if norm in tokens:
                    target_tokens |= tokens

            if hidden:
                self._hidden_apps.add(norm)
            else:
                self._hidden_apps -= target_tokens

            for app in self._cached_apps:
                app["hidden"] = self.is_app_hidden(app)

            self._save_hidden_apps()
            return sorted(self._hidden_apps)

    def _load_cache(self) -> None:
        """Загружает сохранённый список установленных приложений с диска."""
        if not self._cache_file or not self._cache_file.is_file():
            return
        try:
            with open(self._cache_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
            apps = raw.get("apps", []) if isinstance(raw, dict) else raw
            if isinstance(apps, list):
                cleaned = [
                    {**item, "hidden": self.is_app_hidden(item)}
                    for item in apps
                    if isinstance(item, dict)
                    and item.get("name")
                    and not _is_system_or_junk(
                        item.get("name", ""),
                        item.get("executable"),
                        item.get("shortcut"),
                    )
                ]
                if cleaned:
                    self._cached_apps = cleaned
                    try:
                        self._last_scan_time = float(self._cache_file.stat().st_mtime)
                    except OSError:
                        self._last_scan_time = time.time()
                    logger.info("app_indexer_loaded_cache path=%s total=%d", self._cache_file, len(cleaned))
        except Exception as exc:
            logger.debug("app_indexer_cache_load_failed path=%s err=%s", self._cache_file, exc)

    @staticmethod
    def _apps_signature(apps: list[dict[str, Any]]) -> list[tuple[str, str, str, str]]:
        return [
            (
                str(a.get("name") or ""),
                str(a.get("executable") or ""),
                str(a.get("shortcut") or ""),
                str(a.get("category") or ""),
            )
            for a in apps
        ]

    def _save_cache_if_changed(self, prev_apps: list[dict[str, Any]], new_apps: list[dict[str, Any]]) -> None:
        """Перезаписывает JSON-кэш на диске, если список приложений изменился или файла ещё нет."""
        if not self._cache_file:
            return
        if self._cache_file.is_file() and self._apps_signature(prev_apps) == self._apps_signature(new_apps):
            return
        try:
            ensure_application_dirs()
            self._cache_file.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "updated_at": time.time(),
                "total": len(new_apps),
                "apps": new_apps,
            }
            tmp_path = self._cache_file.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            tmp_path.replace(self._cache_file)
            logger.info("app_indexer_saved_cache path=%s total=%d", self._cache_file, len(new_apps))
        except Exception as exc:
            logger.debug("app_indexer_cache_save_failed path=%s err=%s", self._cache_file, exc)

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
                return [{**app, "hidden": self.is_app_hidden(app)} for app in self._cached_apps]

            prev_apps = list(self._cached_apps)
            apps_by_exe: dict[str, dict[str, Any]] = {}
            seen_norm_names: set[str] = set()
            start_dirs = self._custom_start_dirs if self._custom_start_dirs is not None else _WINDOWS_START_MENU_DIRS

            com_initialized = False
            if pythoncom is not None:
                try:
                    pythoncom.CoInitialize()
                    com_initialized = True
                except Exception:
                    pass

            try:
                # 1. Сканирование меню «Пуск» (.lnk)
                for root_dir in start_dirs:
                    if not root_dir.exists():
                        continue
                    try:
                        for lnk_file in root_dir.rglob("*.lnk"):
                            app_name = lnk_file.stem
                            target_exe = _resolve_shortcut_target(lnk_file)
                            exe_str = str(target_exe.resolve()).lower() if target_exe else None
                            lnk_str = str(lnk_file.resolve())

                            if _is_system_or_junk(app_name, exe_str, lnk_str):
                                continue

                            norm_name = _normalize_name(app_name)
                            if exe_str and exe_str.endswith(".exe"):
                                if exe_str not in apps_by_exe:
                                    exe_path = Path(exe_str)
                                    aliases = self._generate_aliases(app_name, exe_path.stem)
                                    entry = {
                                        "id": f"app_{len(apps_by_exe) + 1}",
                                        "name": app_name,
                                        "executable": exe_str,
                                        "shortcut": lnk_str,
                                        "aliases": aliases,
                                        "category": _classify_app(app_name, exe_path.stem),
                                        "source": "start_menu",
                                    }
                                    entry["hidden"] = self.is_app_hidden(entry)
                                    apps_by_exe[exe_str] = entry
                                    if norm_name:
                                        seen_norm_names.add(norm_name)
                            elif not exe_str:
                                # Не дублируем ярлык с тем же нормализованным именем
                                if norm_name and norm_name in seen_norm_names:
                                    continue
                                key = lnk_str.lower()
                                if key not in apps_by_exe:
                                    aliases = self._generate_aliases(app_name, lnk_file.stem)
                                    entry = {
                                        "id": f"app_{len(apps_by_exe) + 1}",
                                        "name": app_name,
                                        "executable": None,
                                        "shortcut": lnk_str,
                                        "aliases": aliases,
                                        "category": _classify_app(app_name, lnk_file.stem),
                                        "source": "start_menu",
                                    }
                                    entry["hidden"] = self.is_app_hidden(entry)
                                    apps_by_exe[key] = entry
                                    if norm_name:
                                        seen_norm_names.add(norm_name)
                    except Exception as exc:
                        logger.debug("app_indexer_scan_start_menu_error root=%s err=%s", root_dir, exc)
            finally:
                if com_initialized and pythoncom is not None:
                    try:
                        pythoncom.CoUninitialize()
                    except Exception:
                        pass

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
                                            name = p.stem.replace("_", " ").title()
                                            if _is_system_or_junk(name, exe_norm):
                                                continue
                                            if exe_norm not in apps_by_exe:
                                                aliases = self._generate_aliases(name, p.stem)
                                                entry = {
                                                    "id": f"app_{len(apps_by_exe) + 1}",
                                                    "name": name,
                                                    "executable": exe_norm,
                                                    "shortcut": None,
                                                    "aliases": aliases,
                                                    "category": _classify_app(name, p.stem),
                                                    "source": "registry",
                                                }
                                                entry["hidden"] = self.is_app_hidden(entry)
                                                apps_by_exe[exe_norm] = entry
                                except (OSError, ValueError):
                                    continue
                    except (OSError, ValueError):
                        continue

            results = sorted(apps_by_exe.values(), key=lambda x: x["name"].lower())
            self._cached_apps = results
            self._last_scan_time = now
            self._save_cache_if_changed(prev_apps, results)
            logger.info("app_indexer_scanned_apps total=%d", len(results))
            return list(results)

    def get_protocol_suggestions(
        self,
        exclude: list[str] | None = None,
        limit: int = 12,
    ) -> list[dict[str, Any]]:
        """Возвращает динамические предложения установленных программ для протоколов без повторов."""
        apps = self.scan_installed_apps()
        excluded_norms = {_normalize_name(x) for x in (exclude or []) if str(x).strip()}
        excluded_raw = {str(x).strip().lower() for x in (exclude or []) if str(x).strip()}

        category_priority = {
            "browser": 0,
            "messenger": 1,
            "gaming": 2,
            "media": 3,
            "streaming": 4,
            "work": 5,
            "utility": 6,
            "app": 7,
        }

        suggestions: list[tuple[int, int, dict[str, Any]]] = []
        seen_keys: set[str] = set()

        for app in apps:
            if self.is_app_hidden(app):
                continue
            name = str(app.get("name") or "").strip()
            if not name:
                continue
            exe = app.get("executable")
            exe_stem = Path(exe).stem if exe else ""
            key = _suggest_key(app)
            if not key or key in seen_keys:
                continue

            # Проверяем, не добавлено ли уже это приложение в протокол
            candidates = {
                _normalize_name(name),
                _normalize_name(key),
                _normalize_name(exe_stem),
                *(_normalize_name(a) for a in app.get("aliases", [])),
            }
            candidates.discard("")
            if (candidates & excluded_norms) or (exe and str(exe).lower() in excluded_raw):
                continue

            seen_keys.add(key)
            category = app.get("category") or _classify_app(name, exe_stem)
            prio = category_priority.get(category, 7)
            source_prio = 0 if app.get("source") == "start_menu" else 1
            suggestions.append((
                prio,
                source_prio,
                {
                    "key": key,
                    "label": name,
                    "category": category,
                    "executable": exe,
                    "aliases": app.get("aliases", []),
                },
            ))

        suggestions.sort(key=lambda item: (item[0], item[1], item[2]["label"].lower()))
        items = [item[2] for item in suggestions]
        if limit > 0:
            return items[:limit]
        return items

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
