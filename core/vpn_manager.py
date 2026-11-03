from __future__ import annotations

import logging
import os
import statistics
import subprocess
import threading
import time
import zipfile
from pathlib import Path
from typing import Any, Iterable

import psutil

logger = logging.getLogger("jarvis.vpn")

NOT_FOUND_MESSAGE = "Не удалось определить местоположение нужных файлов."

# Клиенты, которые умеет запускать JARVIS. Для Happ есть официальный URI-обработчик,
# поэтому кнопку подключения нажимать через UI не нужно. FlClashX запускается как
# обычное приложение, после чего JARVIS пытается нажать кнопку подключения через UIA.
CLIENTS: dict[str, dict[str, Any]] = {
    "happ": {
        "label": "Happ",
        "exe_names": ("happ.exe",),
        "gui_process_names": ("happ.exe",),
        "daemon_process_names": ("happd.exe",),
        "process_names": ("happ.exe", "happd.exe"),
        "keywords": ("happ", "хапп", "хэпп", "хепп"),
        "connect_uri": "happ://connect",
        "disconnect_uri": "happ://disconnect",
        "prefer_uri": True,
    },
    "flclash": {
        "label": "FlClashX",
        "exe_names": ("flclashx.exe", "flclash.exe", "flclash x.exe"),
        "gui_process_names": ("flclashx.exe", "flclash.exe", "flclash x.exe"),
        "daemon_process_names": (
            "clash-meta.exe",
            "mihomo.exe",
            "clash.exe",
            "sing-box.exe",
            "flclash-core.exe",
        ),
        "process_names": (
            "flclashx.exe",
            "flclash.exe",
            "flclash x.exe",
            "clash-meta.exe",
            "mihomo.exe",
            "clash.exe",
            "sing-box.exe",
            "flclash-core.exe",
        ),
        "keywords": ("flclash", "flclashx", "флклэш", "флклаш"),
        "prefer_uri": False,
    },
}

_CLIENT_ALIASES = {
    "happ": "happ",
    "хапп": "happ",
    "хэпп": "happ",
    "хепп": "happ",
    "flclash": "flclash",
    "flclashx": "flclash",
    "flclash x": "flclash",
    "флклэш": "flclash",
    "флклаш": "flclash",
    "флэш": "flclash",
}

_SKIP_DIR_NAMES = {
    "$recycle.bin",
    "system volume information",
    "windows",
    "winsxs",
    "system32",
    "syswow64",
    "recovery",
    "appdata",
    "node_modules",
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "site-packages",
    "cache",
    "caches",
    "temp",
    "tmp",
    "logs",
    "dumps",
    "installer",
    "installers",
    "drivers",
    "backup",
    "backups",
}

_CONNECT_WORDS = (
    "подключ",
    "connect",
    "активир",
    "activate",
    "включ",
    "включить",
    "start",
    "запуст",
    "toggle",
)

_DISCONNECT_WORDS = (
    "отключ",
    "disconnect",
    "выключ",
)

_EXCLUDE_WORDS = _DISCONNECT_WORDS + (
    "stop",
    "стоп",
    "выход",
    "quit",
    "exit",
    "настрой",
    "settings",
    "обнов",
    "update",
    "удал",
    "delete",
    "свернуть",
    "закрыть",
)

_CLICKABLE_TYPES = {
    "ButtonControl",
    "CheckBoxControl",
    "RadioButtonControl",
    "ListItemControl",
    "MenuItemControl",
    "SplitButtonControl",
}


def normalize_client(value: str | None) -> str | None:
    """Приводит пользовательское название клиента к внутреннему id."""
    text = str(value or "").strip().casefold().replace("ё", "е")
    text = " ".join(text.split())
    return _CLIENT_ALIASES.get(text)


def _result(success: bool, *, message: str | None = None, error: str | None = None, **extra: Any) -> dict[str, Any]:
    data: dict[str, Any] = {"success": success}
    if message is not None:
        data["message"] = message
    if error is not None:
        data["error"] = error
    data.update(extra)
    return data


def _process_running(names: Iterable[str]) -> bool:
    wanted = {str(name).casefold() for name in names}
    for proc in psutil.process_iter(["name", "exe"]):
        try:
            name = str(proc.info.get("name") or "").casefold()
            if name in wanted:
                return True
            exe_name = Path(str(proc.info.get("exe") or "")).name.casefold()
            if exe_name in wanted:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            continue
    return False


def _search_roots() -> list[tuple[Path, int]]:
    env = os.environ
    roots: list[tuple[Path, int]] = []

    def add(path: str | Path | None, depth: int) -> None:
        if not path:
            return
        candidate = Path(path).expanduser()
        if candidate.is_dir():
            roots.append((candidate, depth))

    user_home = Path(env.get("USERPROFILE") or Path.home())
    for program_files in (env.get("ProgramFiles"), env.get("ProgramFiles(x86)")):
        add(program_files, 4)
    add(env.get("ProgramData"), 3)
    add(Path(env.get("LOCALAPPDATA", "")) / "Programs", 4)
    add(env.get("LOCALAPPDATA"), 3)
    add(env.get("APPDATA"), 2)
    try:
        from core.app_paths import APP_DATA_DIR

        add(APP_DATA_DIR, 4)
    except Exception:
        pass
    add(user_home / "Desktop", 5)
    add(user_home / "Downloads", 5)
    add(user_home / "Documents", 5)
    add(user_home, 3)

    # Небольшая глубина по корням дисков: там чаще всего лежат портативные сборки.
    for drive in "CDEFGH":
        root = Path(f"{drive}:\\")
        if root.is_dir():
            roots.append((root, 2))

    unique: list[tuple[Path, int]] = []
    seen: set[str] = set()
    for root, depth in roots:
        key = str(root).casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append((root, depth))
    return unique


def _bounded_find_all(
    roots: list[tuple[Path, int]],
    names: Iterable[str],
    *,
    deadline: float,
    limit: int = 40,
) -> list[Path]:
    wanted = {str(name).casefold() for name in names}
    found: list[Path] = []
    stack: list[tuple[Path, int, int]] = [(root, 0, depth) for root, depth in roots]

    while stack and len(found) < limit:
        if time.monotonic() > deadline:
            break
        current, depth, max_depth = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    if time.monotonic() > deadline:
                        break
                    try:
                        if entry.is_file(follow_symlinks=False):
                            if entry.name.casefold() in wanted:
                                found.append(Path(entry.path))
                        elif entry.is_dir(follow_symlinks=False):
                            if depth >= max_depth:
                                continue
                            if entry.name.casefold() in _SKIP_DIR_NAMES:
                                continue
                            stack.append((Path(entry.path), depth + 1, max_depth))
                    except OSError:
                        continue
        except OSError:
            continue
    return found


def _bounded_find_archives(roots: list[tuple[Path, int]], *, deadline: float, limit: int = 20) -> list[Path]:
    found: list[Path] = []
    stack: list[tuple[Path, int, int]] = [(root, 0, depth) for root, depth in roots]

    while stack and len(found) < limit:
        if time.monotonic() > deadline:
            break
        current, depth, max_depth = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    if time.monotonic() > deadline:
                        break
                    try:
                        if entry.is_file(follow_symlinks=False):
                            name = entry.name.casefold()
                            if name.endswith(".zip") and ("zapret" in name or "запрет" in name):
                                found.append(Path(entry.path))
                        elif entry.is_dir(follow_symlinks=False):
                            if depth >= max_depth or entry.name.casefold() in _SKIP_DIR_NAMES:
                                continue
                            stack.append((Path(entry.path), depth + 1, max_depth))
                    except OSError:
                        continue
        except OSError:
            continue
    return found


def _resolve_shortcut(path: Path) -> Path | None:
    try:
        import win32com.client

        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(str(path))
        target = str(getattr(shortcut, "TargetPath", "") or "").strip()
        if target and Path(target).is_file():
            return Path(target)
    except Exception as exc:
        logger.debug("vpn_shortcut_resolve_failed path=%s error=%s", path, exc)
    return None


def _start_menu_shortcuts() -> list[Path]:
    roots = [
        Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
    ]
    shortcuts: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        try:
            shortcuts.extend(root.rglob("*.lnk"))
        except OSError:
            continue
    return shortcuts


def _registry_paths(keywords: Iterable[str], exe_names: Iterable[str]) -> list[Path]:
    keywords = tuple(str(item).casefold() for item in keywords)
    exe_names = {str(item).casefold() for item in exe_names}
    try:
        import winreg
    except ImportError:
        return []

    locations = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall", 0),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall", winreg.KEY_WOW64_64KEY),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall", winreg.KEY_WOW64_32KEY),
    ]
    result: list[Path] = []

    def read_value(key, name: str) -> str:
        try:
            value, _ = winreg.QueryValueEx(key, name)
            return str(value or "").strip()
        except OSError:
            return ""

    for hive, subkey, view in locations:
        try:
            with winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ | view) as root_key:
                count = winreg.QueryInfoKey(root_key)[0]
                for index in range(count):
                    try:
                        with winreg.OpenKey(root_key, winreg.EnumKey(root_key, index)) as app_key:
                            display = read_value(app_key, "DisplayName").casefold()
                            if not display or not any(keyword in display for keyword in keywords):
                                continue
                            icon = read_value(app_key, "DisplayIcon")
                            location = read_value(app_key, "InstallLocation")
                            for raw in (icon, location):
                                cleaned = raw.strip().strip('"')
                                if "," in cleaned:
                                    cleaned = cleaned.rsplit(",", 1)[0].strip().strip('"')
                                if not cleaned:
                                    continue
                                path = Path(cleaned)
                                if path.is_file() and path.name.casefold() in exe_names:
                                    result.append(path)
                                elif path.is_dir():
                                    for exe_name in exe_names:
                                        for candidate in path.glob(exe_name):
                                            if candidate.is_file():
                                                result.append(candidate)
                    except OSError:
                        continue
        except OSError:
            continue
    return result


class VpnManager:
    """Поиск, запуск и активация VPN-клиентов и «Запрета» без жёстких путей."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._cache: dict[str, Any] | None = None
        self._cache_at = 0.0
        self._cache_ttl = 45.0

    # ------------------------------------------------------------------ status

    def status(self, force: bool = False) -> dict[str, Any]:
        with self._lock:
            now = time.monotonic()
            if not force and self._cache is not None and now - self._cache_at < self._cache_ttl:
                return self._cache

            logger.info("vpn_status_discovery_start force=%s", force)
            status = {
                "zapret": self._zapret_status(force=force),
                "clients": {
                    key: self._client_status(key, force=force) for key in CLIENTS
                },
                "not_found_message": NOT_FOUND_MESSAGE,
            }
            self._cache = status
            self._cache_at = time.monotonic()
            logger.info(
                "vpn_status_discovery_finish zapret=%s happ=%s flclash=%s",
                status["zapret"].get("found"),
                status["clients"]["happ"].get("found"),
                status["clients"]["flclash"].get("found"),
            )
            return status

    @staticmethod
    def _is_flclash_vpn_running(definition: dict[str, Any]) -> bool:
        if _process_running(definition.get("daemon_process_names", ())):
            return True
        if _process_running(definition.get("gui_process_names", ())):
            try:
                for iface in psutil.net_if_addrs():
                    lower_name = iface.casefold()
                    if any(x in lower_name for x in ("clash", "mihomo", "meta", "sing-box", "flclash", "tun")):
                        return True
            except Exception:
                pass
        return False

    def _client_status(self, key: str, *, force: bool = False) -> dict[str, Any]:
        definition = CLIENTS[key]
        cached_path, cached = (None, False) if force else self._cached_client_path(key)
        path = cached_path
        if not cached:
            path = self._discover_client(key)

        gui_running = _process_running(definition.get("gui_process_names", ()))
        if key == "flclash":
            vpn_running = self._is_flclash_vpn_running(definition)
        else:
            vpn_running = _process_running(definition.get("daemon_process_names", ()))
        running = bool(gui_running or vpn_running)

        status_notes = []
        status_notes.append("окно открыто" if gui_running else "окно закрыто")
        status_notes.append("VPN работает" if vpn_running else "VPN не активен")
        status_desc = ", ".join(status_notes)

        return {
            "id": key,
            "label": definition["label"],
            "found": bool(path),
            "path": str(path) if path else None,
            "running": running,
            "gui_running": gui_running,
            "vpn_running": vpn_running,
            "message": (
                f"{definition['label']}: найден {path} ({status_desc})"
                if path
                else f"{NOT_FOUND_MESSAGE} {definition['label']} не найден."
            ),
        }

    def _cached_client_path(self, key: str) -> tuple[Path | None, bool]:
        if not self._cache:
            return None, False
        clients = self._cache.get("clients") or {}
        if key not in clients:
            return None, False
        raw = (clients.get(key) or {}).get("path")
        return (Path(raw) if raw else None), True

    def _discover_client(self, key: str) -> Path | None:
        definition = CLIENTS[key]
        exe_names = definition["exe_names"]

        # 1. Уже запущенный клиент: берём путь прямо из процесса.
        for proc in psutil.process_iter(["name", "exe"]):
            try:
                exe = Path(str(proc.info.get("exe") or ""))
                if exe.is_file() and exe.name.casefold() in {name.casefold() for name in exe_names}:
                    logger.info("vpn_client_found source=process key=%s path=%s", key, exe)
                    return exe
            except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                continue

        # 2. Записи установщика (Happ так и находится, даже если ярлыка нет).
        for candidate in _registry_paths(definition["keywords"], exe_names):
            if candidate.is_file():
                logger.info("vpn_client_found source=registry key=%s path=%s", key, candidate)
                return candidate

        # 3. Ярлыки в меню «Пуск».
        for shortcut in _start_menu_shortcuts():
            if not any(keyword in shortcut.stem.casefold() for keyword in definition["keywords"]):
                continue
            target = _resolve_shortcut(shortcut)
            if target and target.name.casefold() in {name.casefold() for name in exe_names}:
                logger.info("vpn_client_found source=shortcut key=%s path=%s", key, target)
                return target

        # 4. Ограниченный поиск по типовым каталогам.
        deadline = time.monotonic() + 8.0
        candidates = _bounded_find_all(_search_roots(), exe_names, deadline=deadline, limit=10)
        if candidates:
            candidates.sort(key=lambda item: (len(item.parts), str(item).casefold()))
            logger.info("vpn_client_found source=filesystem key=%s path=%s", key, candidates[0])
            return candidates[0]

        logger.warning("vpn_client_not_found key=%s", key)
        return None

    def _zapret_status(self, *, force: bool = False) -> dict[str, Any]:
        if not force and self._cache:
            return self._cache.get("zapret") or {}

        winws_running = _process_running(("winws.exe",))
        service_bat = self._find_service_bat()
        if service_bat:
            return {
                "id": "zapret",
                "label": "Запрет Discord/YouTube",
                "found": True,
                "path": str(service_bat),
                "source": "disk",
                "running": winws_running,
                "service_running": winws_running,
                "message": (
                    f"service.bat найден: {service_bat} "
                    f"(служба winws: {'работает' if winws_running else 'остановлена'})"
                ),
            }

        archive = self._find_zapret_archive()
        if archive:
            return {
                "id": "zapret",
                "label": "Запрет Discord/YouTube",
                "found": True,
                "path": str(archive),
                "source": "archive",
                "running": winws_running,
                "service_running": winws_running,
                "message": (
                    f"Найден архив Запрета: {archive}. При запуске он будет распакован. "
                    f"(служба winws: {'работает' if winws_running else 'остановлена'})"
                ),
            }

        return {
            "id": "zapret",
            "label": "Запрет Discord/YouTube",
            "found": False,
            "path": None,
            "source": None,
            "running": winws_running,
            "service_running": winws_running,
            "message": f"{NOT_FOUND_MESSAGE} service.bat от Запрета не найден.",
        }

    @staticmethod
    def _looks_like_zapret(folder: Path) -> bool:
        markers = (
            folder / "bin" / "winws.exe",
            folder / "winws.exe",
            folder / "general.bat",
            folder / "lists",
            folder / "utils",
        )
        return any(marker.exists() for marker in markers)

    def _find_service_bat(self) -> Path | None:
        # Уже распакованный Запрет в данных JARVIS.
        try:
            from core.app_paths import APP_DATA_DIR

            for candidate in (APP_DATA_DIR / "zapret").rglob("service.bat"):
                if candidate.is_file() and self._looks_like_zapret(candidate.parent):
                    return candidate
        except OSError:
            pass

        # Быстрый путь: папки с очевидным именем.
        for root, depth in _search_roots():
            try:
                for entry in root.iterdir():
                    if not entry.is_dir():
                        continue
                    name = entry.name.casefold()
                    if "zapret" not in name and "запрет" not in name:
                        continue
                    for candidate in entry.rglob("service.bat"):
                        if candidate.is_file() and self._looks_like_zapret(candidate.parent):
                            return candidate
            except OSError:
                continue

        deadline = time.monotonic() + 8.0
        for candidate in _bounded_find_all(_search_roots(), ("service.bat",), deadline=deadline, limit=40):
            if self._looks_like_zapret(candidate.parent):
                logger.info("zapret_service_bat_found path=%s", candidate)
                return candidate
        return None

    def _find_zapret_archive(self) -> Path | None:
        deadline = time.monotonic() + 6.0
        for archive in _bounded_find_archives(_search_roots(), deadline=deadline, limit=20):
            try:
                with zipfile.ZipFile(archive) as bundle:
                    if any(Path(name).name.casefold() == "service.bat" for name in bundle.namelist()):
                        logger.info("zapret_archive_found path=%s", archive)
                        return archive
            except (OSError, zipfile.BadZipFile):
                continue
        return None

    # ----------------------------------------------------------------- launch

    def launch_zapret(self) -> dict[str, Any]:
        service_bat = self._find_service_bat()
        if service_bat is None:
            archive = self._find_zapret_archive()
            if archive is not None:
                service_bat = self._extract_zapret(archive)
        if service_bat is None:
            return _result(
                False,
                error=NOT_FOUND_MESSAGE,
                message=f"{NOT_FOUND_MESSAGE} service.bat от Запрета не найден.",
            )

        try:
            logger.info("zapret_launch path=%s", service_bat)
            os.startfile(str(service_bat))
        except OSError as exc:
            logger.exception("zapret_launch_failed path=%s", service_bat)
            return _result(
                False,
                error=str(exc),
                message=f"Не удалось открыть service.bat: {exc}",
                path=str(service_bat),
            )

        # Сбрасываем кэш, чтобы следующий status увидел свежий winws.exe.
        with self._lock:
            self._cache = None
        return _result(
            True,
            message=f"Открываю service.bat Запрета: {service_bat.name}.",
            path=str(service_bat),
            running=_process_running(("winws.exe",)),
        )

    @staticmethod
    def _extract_zapret(archive: Path) -> Path | None:
        from core.app_paths import APP_DATA_DIR

        target = APP_DATA_DIR / "zapret"
        target.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(archive) as bundle:
                base = target.resolve()
                for member in bundle.infolist():
                    destination = (target / member.filename).resolve()
                    if destination != base and base not in destination.parents:
                        logger.warning("zapret_archive_unsafe_member member=%s", member.filename)
                        continue
                    bundle.extract(member, target)
        except (OSError, zipfile.BadZipFile) as exc:
            logger.exception("zapret_extract_failed archive=%s", archive)
            return None

        candidates = sorted(target.rglob("service.bat"), key=lambda item: (len(item.parts), str(item).casefold()))
        for candidate in candidates:
            if candidate.is_file() and VpnManager._looks_like_zapret(candidate.parent):
                logger.info("zapret_extracted archive=%s path=%s", archive, candidate)
                return candidate
        return None

    def connect(self, client: str | None = None) -> dict[str, Any]:
        key = normalize_client(client)
        if key is None:
            key = self._default_client()
        if key is None:
            return _result(
                False,
                error=NOT_FOUND_MESSAGE,
                message=f"{NOT_FOUND_MESSAGE} Ни Happ, ни FlClashX не найдены.",
            )

        definition = CLIENTS[key]
        path, cached = self._cached_client_path(key)
        if not cached:
            path = self._discover_client(key)
        if path is None:
            return _result(
                False,
                error=NOT_FOUND_MESSAGE,
                message=f"{NOT_FOUND_MESSAGE} {definition['label']} не найден.",
                client=key,
            )

        if key == "happ" and definition.get("prefer_uri"):
            return self._connect_happ(path, definition)
        return self._connect_with_ui(key, path, definition)

    def _default_client(self) -> str | None:
        for key in ("happ", "flclash"):
            if self.status().get("clients", {}).get(key, {}).get("found"):
                return key
        return None

    def _connect_happ(self, path: Path, definition: dict[str, Any]) -> dict[str, Any]:
        uri = str(definition.get("connect_uri") or "")
        try:
            logger.info("happ_connect_uri uri=%s", uri)
            os.startfile(uri)
        except OSError as exc:
            logger.warning("happ_connect_uri_failed uri=%s error=%s", uri, exc)
            return self._connect_with_ui("happ", path, definition)

        with self._lock:
            self._cache = None
        return _result(
            True,
            message="Happ запущен, команда подключения отправлена.",
            client="happ",
            path=str(path),
            launched=True,
            activated=True,
            method="uri",
        )

    def _connect_with_ui(self, key: str, path: Path, definition: dict[str, Any]) -> dict[str, Any]:
        launched = False
        if not _process_running(definition["gui_process_names"]):
            try:
                logger.info("vpn_client_launch key=%s path=%s", key, path)
                subprocess.Popen([str(path)], cwd=str(path.parent))
                launched = True
            except OSError as exc:
                logger.exception("vpn_client_launch_failed key=%s path=%s", key, path)
                return _result(
                    False,
                    error=str(exc),
                    message=f"Не удалось запустить {definition['label']}: {exc}",
                    client=key,
                    path=str(path),
                )

        activated, already_active, detail = self._activate_with_uia(key, timeout=14.0)
        with self._lock:
            self._cache = None

        if activated:
            message = (
                f"{definition['label']}: VPN уже подключён."
                if already_active
                else f"{definition['label']} запущен, кнопка подключения нажата."
            )
            return _result(
                True,
                message=message,
                client=key,
                path=str(path),
                launched=launched,
                activated=True,
                already_active=already_active,
                method="uia",
                detail=detail,
            )

        return _result(
            True,
            error=None,
            message=(
                f"{definition['label']} запущен, но кнопку подключения нажать автоматически "
                f"не удалось ({detail}). Нажми её вручную."
            ),
            client=key,
            path=str(path),
            launched=launched,
            activated=False,
            method="uia",
            detail=detail,
        )

    def _activate_with_uia(self, key: str, timeout: float = 14.0) -> tuple[bool, bool, str]:
        try:
            import uiautomation as auto
        except ImportError:
            logger.warning("uiautomation_not_installed")
            return False, False, "модуль uiautomation не установлен"

        deadline = time.monotonic() + timeout
        definition = CLIENTS[key]
        pids = self._collect_pids(definition)
        last_error = "окно клиента не найдено"

        try:
            with auto.UIAutomationInitializerInThread():
                window = None
                while time.monotonic() < deadline:
                    pids = self._collect_pids(definition)
                    window = self._find_uia_window(auto, pids)
                    if window is not None:
                        break
                    time.sleep(0.5)
                if window is None:
                    return False, False, last_error

                try:
                    window.SetActive()
                    window.SetFocus()
                except Exception:
                    pass

                controls = list(self._iter_uia_controls(window, max_depth=14, max_count=900))
                logger.info("uia_controls_collected key=%s count=%d", key, len(controls))

                disconnect = self._find_clickable(controls, _DISCONNECT_WORDS, exclude=_CONNECT_WORDS)
                candidates = self._find_clickable(controls, _CONNECT_WORDS, exclude=_EXCLUDE_WORDS)
                candidates.sort(key=lambda ctrl: (ctrl.ControlTypeName != "ButtonControl", -self._control_area(ctrl)))

                for candidate in candidates[:6]:
                    name = self._control_text(candidate)
                    try:
                        candidate.Click(simulateMove=False)
                        return True, False, f"нажата кнопка «{name}»"
                    except Exception as exc:
                        last_error = f"не удалось нажать «{name}»: {exc}"
                        try:
                            candidate.GetInvokePattern().Invoke()
                            return True, False, f"нажата кнопка «{name}»"
                        except Exception:
                            continue

                if disconnect is not None:
                    return True, True, f"найдена кнопка «{self._control_text(disconnect)}»"

                fallback = self._largest_unlabeled_button(controls)
                if fallback is not None:
                    try:
                        fallback.Click(simulateMove=False)
                        return True, False, "нажата самая крупная кнопка на экране"
                    except Exception as exc:
                        last_error = f"не удалось нажать крупную кнопку: {exc}"
        except Exception as exc:
            logger.exception("uia_activation_failed key=%s", key)
            last_error = str(exc)

        return False, False, last_error

    @staticmethod
    def _collect_pids(definition: dict[str, Any]) -> set[int]:
        wanted = {name.casefold() for name in definition["gui_process_names"]}
        pids: set[int] = set()
        for proc in psutil.process_iter(["pid", "name", "exe"]):
            try:
                name = str(proc.info.get("name") or "").casefold()
                exe_name = Path(str(proc.info.get("exe") or "")).name.casefold()
                if name in wanted or exe_name in wanted:
                    pids.add(int(proc.info["pid"]))
            except (psutil.NoSuchProcess, psutil.AccessDenied, OSError, KeyError):
                continue
        return pids

    @staticmethod
    def _find_uia_window(auto, pids: set[int]):
        if not pids:
            return None
        try:
            root = auto.GetRootControl()
            for window in root.GetChildren():
                try:
                    if window.ProcessId not in pids:
                        continue
                    if window.ControlTypeName != "WindowControl":
                        continue
                    if not window.Name and not window.BoundingRectangle:
                        continue
                    return window
                except Exception:
                    continue
        except Exception:
            return None
        return None

    @staticmethod
    def _iter_uia_controls(control, max_depth: int = 14, max_count: int = 900):
        stack = [(control, 0)]
        yielded = 0
        while stack and yielded < max_count:
            current, depth = stack.pop()
            yield current
            yielded += 1
            if depth >= max_depth:
                continue
            try:
                children = current.GetChildren()
            except Exception:
                children = []
            for child in reversed(children):
                stack.append((child, depth + 1))

    @staticmethod
    def _control_text(control) -> str:
        parts = []
        for attribute in ("Name", "AutomationId", "HelpText"):
            try:
                value = getattr(control, attribute, "")
                if value:
                    parts.append(str(value))
            except Exception:
                continue
        return " ".join(parts).casefold().replace("ё", "е")

    @classmethod
    def _find_clickable(cls, controls: list[Any], words: Iterable[str], *, exclude: Iterable[str] = ()):
        words = tuple(str(word).casefold() for word in words)
        exclude = tuple(str(word).casefold() for word in exclude)
        result = []
        for control in controls:
            try:
                if control.ControlTypeName not in _CLICKABLE_TYPES:
                    continue
                if not control.IsEnabled or control.IsOffscreen:
                    continue
            except Exception:
                continue
            text = cls._control_text(control)
            if not text:
                continue
            if any(word in text for word in exclude):
                continue
            if any(word in text for word in words):
                result.append(control)
        return result

    @classmethod
    def _largest_unlabeled_button(cls, controls: list[Any]):
        buttons = []
        for control in controls:
            try:
                if control.ControlTypeName != "ButtonControl":
                    continue
                if not control.IsEnabled or control.IsOffscreen:
                    continue
                name = str(control.Name or "").strip()
                if name:
                    continue
            except Exception:
                continue
            area = cls._control_area(control)
            if area >= 2500:
                buttons.append((area, control))
        if not buttons:
            return None
        buttons.sort(key=lambda item: item[0], reverse=True)
        areas = [area for area, _ in buttons]
        median = statistics.median(areas)
        if len(buttons) == 1 or buttons[0][0] >= max(median * 2.5, 2500):
            return buttons[0][1]
        return None

    @staticmethod
    def _control_area(control) -> int:
        try:
            rect = control.BoundingRectangle
            width = max(0, int(rect.right - rect.left))
            height = max(0, int(rect.bottom - rect.top))
            return width * height
        except Exception:
            return 0


_manager: VpnManager | None = None
_manager_lock = threading.Lock()


def get_vpn_manager() -> VpnManager:
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = VpnManager()
        return _manager
