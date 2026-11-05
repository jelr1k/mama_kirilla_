from __future__ import annotations

import logging
import os
import time
import zipfile
from pathlib import Path
from typing import Any

from core.vpn.constants import NOT_FOUND_MESSAGE, result_dict
from core.vpn.discovery import (
    bounded_find_all,
    bounded_find_archives,
    process_running,
    search_roots,
)

logger = logging.getLogger("jarvis.vpn.zapret")


def looks_like_zapret(folder: Path) -> bool:
    """Проверяет маркеры, характерные для папки со сборкой Zapret."""
    markers = (
        folder / "bin" / "winws.exe",
        folder / "winws.exe",
        folder / "general.bat",
        folder / "lists",
        folder / "utils",
    )
    return any(marker.exists() for marker in markers)


def find_service_bat() -> Path | None:
    """Ищет service.bat Запрета в AppData, типовых каталогах и корнях дисков."""
    # Уже распакованный Запрет в данных JARVIS.
    try:
        from core.app_paths import APP_DATA_DIR

        for candidate in (APP_DATA_DIR / "zapret").rglob("service.bat"):
            if candidate.is_file() and looks_like_zapret(candidate.parent):
                return candidate
    except OSError:
        pass

    # Быстрый путь: папки с очевидным именем.
    for root, depth in search_roots():
        try:
            for entry in root.iterdir():
                if not entry.is_dir():
                    continue
                name = entry.name.casefold()
                if "zapret" not in name and "запрет" not in name:
                    continue
                for candidate in entry.rglob("service.bat"):
                    if candidate.is_file() and looks_like_zapret(candidate.parent):
                        return candidate
        except OSError:
            continue

    deadline = time.monotonic() + 8.0
    for candidate in bounded_find_all(search_roots(), ("service.bat",), deadline=deadline, limit=40):
        if looks_like_zapret(candidate.parent):
            logger.info("zapret_service_bat_found path=%s", candidate)
            return candidate
    return None


def find_zapret_archive() -> Path | None:
    """Ищет zip-архив со сборкой Запрета."""
    deadline = time.monotonic() + 6.0
    for archive in bounded_find_archives(search_roots(), deadline=deadline, limit=20):
        try:
            with zipfile.ZipFile(archive) as bundle:
                if any(Path(name).name.casefold() == "service.bat" for name in bundle.namelist()):
                    logger.info("zapret_archive_found path=%s", archive)
                    return archive
        except (OSError, zipfile.BadZipFile):
            continue
    return None


def extract_zapret(archive: Path) -> Path | None:
    """Распаковывает zip-архив Запрета в рабочую директорию AppData JARVIS."""
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
        if candidate.is_file() and looks_like_zapret(candidate.parent):
            logger.info("zapret_extracted archive=%s path=%s", archive, candidate)
            return candidate
    return None


def get_zapret_status_data(
    service_bat: Path | None,
    archive: Path | None,
) -> dict[str, Any]:
    """Формирует статус Zapret на основе обнаруженных путей."""
    winws_running = process_running(("winws.exe",))
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


def launch_service_bat(service_bat: Path) -> dict[str, Any]:
    """Запускает найденный service.bat Запрета."""
    try:
        logger.info("zapret_launch path=%s", service_bat)
        os.startfile(str(service_bat))
    except OSError as exc:
        logger.exception("zapret_launch_failed path=%s", service_bat)
        return result_dict(
            False,
            error=str(exc),
            message=f"Не удалось открыть service.bat: {exc}",
            path=str(service_bat),
        )

    return result_dict(
        True,
        message=f"Открываю service.bat Запрета: {service_bat.name}.",
        path=str(service_bat),
        running=process_running(("winws.exe",)),
    )
