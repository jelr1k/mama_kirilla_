"""Legacy PySide6 presentation controllers for Jarvis.

These controllers were used by the original PySide6 GUI (now archived in `ui_archive/`).
In the modern Tauri v2 architecture, the frontend communicates with the backend
via the Gateway WebSocket/REST API (`services/gateway/`).
"""

import importlib
import warnings

warnings.warn(
    "presentation.legacy contains deprecated PySide6 controllers retained only for ui_archive.",
    DeprecationWarning,
    stacklevel=2,
)

_CONTROLLER_MAP = {
    "AliasController": "alias_controller",
    "ApplicationController": "application_controller",
    "ChatController": "chat_controller",
    "DependencyController": "dependency_controller",
    "OllamaController": "ollama_controller",
    "ProtocolsController": "protocols_controller",
    "SettingsController": "settings_controller",
    "StatisticsController": "statistics_controller",
    "ToolsController": "tools_controller",
    "VoiceController": "voice_controller",
    "WakeWordController": "wake_word_controller",
    "WebsitesController": "websites_controller",
    "WorkspaceController": "workspace_controller",
}

__all__ = list(_CONTROLLER_MAP.keys())


def __getattr__(name: str):
    if name in _CONTROLLER_MAP:
        mod_name = _CONTROLLER_MAP[name]
        mod = importlib.import_module(f"presentation.legacy.{mod_name}")
        cls = getattr(mod, name)
        globals()[name] = cls
        return cls
    raise AttributeError(f"module 'presentation.legacy' has no attribute '{name}'")


def __dir__():
    return sorted(set(list(globals().keys()) + __all__))
