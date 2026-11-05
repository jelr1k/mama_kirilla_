from __future__ import annotations

from typing import Any

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


def result_dict(success: bool, *, message: str | None = None, error: str | None = None, **extra: Any) -> dict[str, Any]:
    """Формирует унифицированный словарь ответа операции."""
    data: dict[str, Any] = {"success": success}
    if message is not None:
        data["message"] = message
    if error is not None:
        data["error"] = error
    data.update(extra)
    return data
