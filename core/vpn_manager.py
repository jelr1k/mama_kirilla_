from __future__ import annotations

import logging
import os
import subprocess
import time
import zipfile
from typing import Any

import psutil

import core.vpn.manager as _vpn_mgr_mod
from core.vpn.constants import (
    CLIENTS,
    NOT_FOUND_MESSAGE,
    _CLICKABLE_TYPES,
    _CLIENT_ALIASES,
    _CONNECT_WORDS,
    _DISCONNECT_WORDS,
    _EXCLUDE_WORDS,
    _SKIP_DIR_NAMES,
    normalize_client,
    result_dict as _result,
)
from core.vpn.discovery import (
    bounded_find_all as _bounded_find_all,
    bounded_find_archives as _bounded_find_archives,
    discover_client_path,
    process_running as _process_running,
    registry_paths as _registry_paths,
    resolve_shortcut as _resolve_shortcut,
    search_roots as _search_roots,
    start_menu_shortcuts as _start_menu_shortcuts,
)
from core.vpn.manager import (
    VpnManager,
    _manager_lock,
    get_vpn_manager,
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

import sys

# Для 100% обратной совместимости живого синглтона vm._manager
class _VpnManagerModule(sys.modules[__name__].__class__):
    @property
    def _manager(self) -> Any:
        return _vpn_mgr_mod._manager

    @_manager.setter
    def _manager(self, value: Any) -> None:
        _vpn_mgr_mod._manager = value


sys.modules[__name__].__class__ = _VpnManagerModule


__all__ = [
    "CLIENTS",
    "NOT_FOUND_MESSAGE",
    "VpnManager",
    "_CLICKABLE_TYPES",
    "_CLIENT_ALIASES",
    "_CONNECT_WORDS",
    "_DISCONNECT_WORDS",
    "_EXCLUDE_WORDS",
    "_SKIP_DIR_NAMES",
    "_bounded_find_all",
    "_bounded_find_archives",
    "_manager",
    "_manager_lock",
    "_process_running",
    "_registry_paths",
    "_resolve_shortcut",
    "_result",
    "_search_roots",
    "_start_menu_shortcuts",
    "get_vpn_manager",
    "normalize_client",
    "os",
    "psutil",
    "subprocess",
    "time",
    "zipfile",
]
