from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any, Iterable

import psutil

from core.vpn.constants import CLIENTS, _SKIP_DIR_NAMES

logger = logging.getLogger("jarvis.vpn.discovery")


def process_running(names: Iterable[str]) -> bool:
    """Проверяет, запущен ли хотя бы один процесс с указанным именем исполняемого файла."""
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


def search_roots() -> list[tuple[Path, int]]:
    """Возвращает список стартовых каталогов для поиска с ограничением глубины."""
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


def bounded_find_all(
    roots: list[tuple[Path, int]],
    names: Iterable[str],
    *,
    deadline: float,
    limit: int = 40,
) -> list[Path]:
    """Ищет файлы с заданными именами в указанных каталогах с лимитом по времени и количеству."""
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


def bounded_find_archives(roots: list[tuple[Path, int]], *, deadline: float, limit: int = 20) -> list[Path]:
    """Ищет zip-архивы Запрета с лимитом по времени."""
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


def resolve_shortcut(path: Path) -> Path | None:
    """Разрешает путь Windows shortcut (.lnk)."""
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


def start_menu_shortcuts() -> list[Path]:
    """Сканирует ярлыки в меню «Пуск» пользователя и системы."""
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


def registry_paths(keywords: Iterable[str], exe_names: Iterable[str]) -> list[Path]:
    """Ищет установленные приложения в системном реестре Windows."""
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


def discover_client_path(key: str) -> Path | None:
    """Обнаруживает путь к исполняемому файлу клиента (процессы -> реестр -> ярлыки -> ФС)."""
    definition = CLIENTS.get(key)
    if not definition:
        return None
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
    for candidate in registry_paths(definition["keywords"], exe_names):
        if candidate.is_file():
            logger.info("vpn_client_found source=registry key=%s path=%s", key, candidate)
            return candidate

    # 3. Ярлыки в меню «Пуск».
    for shortcut in start_menu_shortcuts():
        if not any(keyword in shortcut.stem.casefold() for keyword in definition["keywords"]):
            continue
        target = resolve_shortcut(shortcut)
        if target and target.name.casefold() in {name.casefold() for name in exe_names}:
            logger.info("vpn_client_found source=shortcut key=%s path=%s", key, target)
            return target

    # 4. Ограниченный поиск по типовым каталогам.
    deadline = time.monotonic() + 8.0
    candidates = bounded_find_all(search_roots(), exe_names, deadline=deadline, limit=10)
    if candidates:
        candidates.sort(key=lambda item: (len(item.parts), str(item).casefold()))
        logger.info("vpn_client_found source=filesystem key=%s path=%s", key, candidates[0])
        return candidates[0]

    logger.warning("vpn_client_not_found key=%s", key)
    return None
