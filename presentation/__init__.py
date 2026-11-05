"""Presentation layer for Jarvis (Kirieshka v2).

In the modern Tauri v2 architecture, the presentation layer contains only
the desktop system tray controller (tray_icon.py).

The legacy PySide6 GUI controllers have been isolated into `presentation.legacy`.
"""

from __future__ import annotations

import importlib
import importlib.machinery
import sys
import types
import warnings

from presentation.tray_icon import create_system_tray, create_tray_pixmap

__all__ = ["create_system_tray", "create_tray_pixmap"]

_LEGACY_MODULES = {
    "alias_controller",
    "application_controller",
    "chat_controller",
    "dependency_controller",
    "ollama_controller",
    "protocols_controller",
    "settings_controller",
    "statistics_controller",
    "tools_controller",
    "voice_controller",
    "wake_word_controller",
    "websites_controller",
    "workspace_controller",
}


class _LegacyProxyModule(types.ModuleType):
    """Transparent proxy that delegates reads/writes to the real presentation.legacy module.

    Ensures full backward compatibility for both attribute access and test patching (monkeypatch).
    """

    def __init__(self, fullname: str, target: types.ModuleType):
        super().__init__(fullname)
        object.__setattr__(self, "_target", target)
        self.__dict__.update(target.__dict__)

    def __getattr__(self, name: str):
        return getattr(self._target, name)

    def __setattr__(self, name: str, value):
        self.__dict__[name] = value
        setattr(self._target, name, value)

    def __dir__(self):
        return sorted(set(super().__dir__() | set(dir(self._target))))


class _LegacyAliasLoader:
    def __init__(self, target_module: types.ModuleType):
        self.target_module = target_module

    def create_module(self, spec: importlib.machinery.ModuleSpec) -> types.ModuleType:
        return _LegacyProxyModule(spec.name, self.target_module)

    def exec_module(self, module: types.ModuleType) -> None:
        pass


class _LegacyPresentationFinder:
    @classmethod
    def find_spec(cls, fullname: str, path=None, target=None):
        if fullname.startswith("presentation.") and not fullname.startswith("presentation.legacy."):
            subname = fullname[len("presentation."):]
            if subname in _LEGACY_MODULES:
                warnings.warn(
                    f"{fullname} has been moved to presentation.legacy.{subname} and is deprecated.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                legacy_mod = importlib.import_module(f"presentation.legacy.{subname}")
                loader = _LegacyAliasLoader(legacy_mod)
                return importlib.machinery.ModuleSpec(fullname, loader)
        return None


# Ensure finder is installed once
sys.meta_path = [f for f in sys.meta_path if getattr(f, "__name__", "") != "_LegacyPresentationFinder"]
sys.meta_path.insert(0, _LegacyPresentationFinder)


def __getattr__(name: str):
    if name in _LEGACY_MODULES:
        warnings.warn(
            f"presentation.{name} has been moved to presentation.legacy.{name} and is deprecated.",
            DeprecationWarning,
            stacklevel=2,
        )
        mod = importlib.import_module(f"presentation.legacy.{name}")
        proxy = _LegacyProxyModule(f"presentation.{name}", mod)
        sys.modules[f"presentation.{name}"] = proxy
        globals()[name] = proxy
        return proxy
    raise AttributeError(f"module 'presentation' has no attribute '{name}'")
