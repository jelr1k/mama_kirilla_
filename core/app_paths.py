from __future__ import annotations

import os
import sys
from pathlib import Path


import shutil


def get_application_root() -> Path:
    """Возвращает каталог установки/размещения приложения.

    В исходниках это корень репозитория, в собранном приложении это каталог
    рядом с реально запущенным .exe. Путь не зависит от буквы диска.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def get_resource_root() -> Path:
    """Возвращает каталог ресурсов, включая поддержку PyInstaller."""
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root).resolve()
    return get_application_root()


APP_ROOT = get_application_root()
RESOURCE_ROOT = get_resource_root()
WORKSPACE_DIR = APP_ROOT / "workspace"

# Local user data (logs, binary caches, session tokens)
_LOCAL_BASE = Path(os.environ.get("LOCALAPPDATA", APP_ROOT / "local_data"))
_PRIMARY_LOCAL = _LOCAL_BASE / "Assistant"
_LEGACY_LOCAL = _LOCAL_BASE / "Jarvis"
LOCAL_DATA_DIR = _PRIMARY_LOCAL
LOG_DIR = LOCAL_DATA_DIR / "logs"
MODELS_DIR = LOCAL_DATA_DIR / "models"
SESSION_TOKEN_PATH = LOCAL_DATA_DIR / "session.token"

# Roaming user configuration & persistent profiles
_ROAMING_BASE = Path(os.environ.get("APPDATA", APP_ROOT / "user_data"))
_PRIMARY_ROAMING = _ROAMING_BASE / "Assistant"
_LEGACY_ROAMING = _ROAMING_BASE / "Jarvis"
APP_DATA_DIR = _PRIMARY_ROAMING
CONFIG_FILE = APP_DATA_DIR / "settings.json"
ALIASES_FILE = APP_DATA_DIR / "aliases.json"
WEBSITES_FILE = APP_DATA_DIR / "websites.json"
PROTOCOLS_FILE = APP_DATA_DIR / "protocols.json"


def _migrate_legacy_files(src_dir: Path, dst_dir: Path) -> None:
    if not src_dir.is_dir():
        return
    for item in src_dir.iterdir():
        target = dst_dir / item.name
        if not target.exists():
            try:
                if item.is_file():
                    shutil.copy2(item, target)
                elif item.is_dir() and item.name not in ("logs", "__pycache__"):
                    shutil.copytree(item, target)
            except OSError:
                pass


def ensure_application_dirs() -> None:
    """Создаёт каталоги, которые нужны приложению во время работы."""
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # При старте переносим файлы из старой папки Jarvis при её наличии (однократно)
    roaming_marker = APP_DATA_DIR / ".migrated"
    if _LEGACY_ROAMING.is_dir() and not roaming_marker.exists():
        _migrate_legacy_files(_LEGACY_ROAMING, APP_DATA_DIR)
        roaming_marker.touch()

    local_marker = LOCAL_DATA_DIR / ".migrated"
    if _LEGACY_LOCAL.is_dir() and not local_marker.exists():
        _migrate_legacy_files(_LEGACY_LOCAL, LOCAL_DATA_DIR)
        local_marker.touch()


def bundled_config_path() -> Path:
    return RESOURCE_ROOT / "config" / "settings.json"
