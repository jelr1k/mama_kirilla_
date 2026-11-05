from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Iterable

from core.vpn.constants import (
    CLIENTS,
    NOT_FOUND_MESSAGE,
    normalize_client,
    result_dict,
)
from core.vpn.discovery import (
    bounded_find_all,
    bounded_find_archives,
    discover_client_path,
    process_running,
    registry_paths,
    resolve_shortcut,
    search_roots,
    start_menu_shortcuts,
)
from core.vpn.uia_driver import (
    activate_with_uia,
    collect_pids,
    control_area,
    control_text,
    find_clickable,
    find_uia_window,
    is_flclash_vpn_running,
    iter_uia_controls,
    largest_unlabeled_button,
)
from core.vpn.zapret_controller import (
    extract_zapret,
    find_service_bat,
    find_zapret_archive,
    get_zapret_status_data,
    launch_service_bat,
    looks_like_zapret,
)

logger = logging.getLogger("jarvis.vpn")


def _get_mod_attr(name: str, fallback: Any) -> Any:
    mod = sys.modules.get("core.vpn_manager")
    if mod is not None:
        return getattr(mod, name, fallback)
    return fallback


def _is_proc_running(names: Iterable[str]) -> bool:
    """Проверяет процесс через core.vpn_manager._process_running (для обратной совместимости monkeypatch)."""
    checker = _get_mod_attr("_process_running", process_running)
    try:
        return checker(names)
    except Exception:
        return process_running(names)


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
            status_data = {
                "zapret": self._zapret_status(force=force),
                "clients": {
                    key: self._client_status(key, force=force) for key in CLIENTS
                },
                "not_found_message": NOT_FOUND_MESSAGE,
            }
            self._cache = status_data
            self._cache_at = time.monotonic()
            logger.info(
                "vpn_status_discovery_finish zapret=%s happ=%s flclash=%s",
                status_data["zapret"].get("found"),
                status_data["clients"]["happ"].get("found"),
                status_data["clients"]["flclash"].get("found"),
            )
            return status_data

    @staticmethod
    def _is_flclash_vpn_running(definition: dict[str, Any]) -> bool:
        return is_flclash_vpn_running(definition, proc_checker=_is_proc_running)

    def _client_status(self, key: str, *, force: bool = False) -> dict[str, Any]:
        definition = CLIENTS[key]
        cached_path, cached = (None, False) if force else self._cached_client_path(key)
        path = cached_path
        if not cached:
            path = self._discover_client(key)

        gui_running = _is_proc_running(definition.get("gui_process_names", ()))
        if key == "flclash":
            vpn_running = self._is_flclash_vpn_running(definition)
        else:
            vpn_running = _is_proc_running(definition.get("daemon_process_names", ()))
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
        return discover_client_path(key)

    def _zapret_status(self, *, force: bool = False) -> dict[str, Any]:
        if not force and self._cache:
            return self._cache.get("zapret") or {}

        service_bat = self._find_service_bat()
        archive = None if service_bat else self._find_zapret_archive()

        winws_running = _is_proc_running(("winws.exe",))
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

    @staticmethod
    def _looks_like_zapret(folder: Path) -> bool:
        return looks_like_zapret(folder)

    def _find_service_bat(self) -> Path | None:
        # Проверяем распакованный Запрет в данных JARVIS
        try:
            from core.app_paths import APP_DATA_DIR

            for candidate in (APP_DATA_DIR / "zapret").rglob("service.bat"):
                if candidate.is_file() and self._looks_like_zapret(candidate.parent):
                    return candidate
        except OSError:
            pass

        roots = _get_mod_attr("_search_roots", search_roots)()
        for root, _ in roots:
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
        finder = _get_mod_attr("_bounded_find_all", bounded_find_all)
        for candidate in finder(roots, ("service.bat",), deadline=deadline, limit=40):
            if self._looks_like_zapret(candidate.parent):
                logger.info("zapret_service_bat_found path=%s", candidate)
                return candidate
        return None

    def _find_zapret_archive(self) -> Path | None:
        roots = _get_mod_attr("_search_roots", search_roots)()
        finder = _get_mod_attr("_bounded_find_archives", bounded_find_archives)
        deadline = time.monotonic() + 6.0
        for archive in finder(roots, deadline=deadline, limit=20):
            try:
                import zipfile
                with zipfile.ZipFile(archive) as bundle:
                    if any(Path(name).name.casefold() == "service.bat" for name in bundle.namelist()):
                        logger.info("zapret_archive_found path=%s", archive)
                        return archive
            except (OSError, Exception):
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
            return result_dict(
                False,
                error=NOT_FOUND_MESSAGE,
                message=f"{NOT_FOUND_MESSAGE} service.bat от Запрета не найден.",
            )

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

        with self._lock:
            self._cache = None
        return result_dict(
            True,
            message=f"Открываю service.bat Запрета: {service_bat.name}.",
            path=str(service_bat),
            running=_is_proc_running(("winws.exe",)),
        )

    @staticmethod
    def _extract_zapret(archive: Path) -> Path | None:
        return extract_zapret(archive)

    def connect(self, client: str | None = None) -> dict[str, Any]:
        key = normalize_client(client)
        if key is None:
            key = self._default_client()
        if key is None:
            return result_dict(
                False,
                error=NOT_FOUND_MESSAGE,
                message=f"{NOT_FOUND_MESSAGE} Ни Happ, ни FlClashX не найдены.",
            )

        definition = CLIENTS[key]
        path, cached = self._cached_client_path(key)
        if not cached:
            path = self._discover_client(key)
        if path is None:
            return result_dict(
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
        return result_dict(
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
        if not _is_proc_running(definition["gui_process_names"]):
            try:
                logger.info("vpn_client_launch key=%s path=%s", key, path)
                subprocess.Popen([str(path)], cwd=str(path.parent))
                launched = True
            except OSError as exc:
                logger.exception("vpn_client_launch_failed key=%s path=%s", key, path)
                return result_dict(
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
            return result_dict(
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

        return result_dict(
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
        return activate_with_uia(key, timeout=timeout, driver=self)

    # UIA helper methods for backwards compatibility
    _collect_pids = staticmethod(collect_pids)
    _find_uia_window = staticmethod(find_uia_window)
    _iter_uia_controls = staticmethod(iter_uia_controls)
    _control_text = staticmethod(control_text)
    _find_clickable = classmethod(lambda cls, controls, words, exclude=(): find_clickable(controls, words, exclude=exclude))
    _largest_unlabeled_button = classmethod(lambda cls, controls: largest_unlabeled_button(controls))
    _control_area = staticmethod(control_area)


_manager: VpnManager | None = None
_manager_lock = threading.Lock()


def get_vpn_manager() -> VpnManager:
    """Возвращает глобальный экземпляр VpnManager (синглтон)."""
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = VpnManager()
        return _manager
