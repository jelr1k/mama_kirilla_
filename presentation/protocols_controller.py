from __future__ import annotations

from typing import Any
from PySide6.QtCore import QObject, Signal

from core.protocols_manager import ProtocolsManager
from services.stark_protocols import StarkProtocols


class ProtocolsController(QObject):
    """Контроллер для взаимодействия UI со службой протоколов JARVIS."""

    changed = Signal()
    profile_changed = Signal(str)

    def __init__(self, manager: ProtocolsManager | None = None, config=None):
        super().__init__()
        self._manager = manager or ProtocolsManager()
        self._config = config

    def list_profiles(self) -> dict[str, str]:
        return self._manager.list_profiles()

    def get_active_profile(self) -> str:
        return self._manager.get_active_profile()

    def set_active_profile(self, profile_id: str) -> bool:
        res = self._manager.set_active_profile(profile_id)
        if res:
            self.profile_changed.emit(profile_id)
            self.changed.emit()
        return res

    def add_profile(self, name: str) -> str:
        pid = self._manager.add_profile(name)
        self.profile_changed.emit(pid)
        self.changed.emit()
        return pid

    def delete_profile(self, profile_id: str) -> bool:
        res = self._manager.delete_profile(profile_id)
        if res:
            self.profile_changed.emit(self.get_active_profile())
            self.changed.emit()
        return res

    def get_protocols(self) -> list[dict[str, Any]]:
        return self._manager.get_protocols()

    def get_protocol(self, protocol_id: str) -> dict[str, Any] | None:
        return self._manager.get_protocol_by_id(protocol_id)

    def save_protocol(self, protocol_data: dict[str, Any]) -> str:
        pid = self._manager.save_protocol(protocol_data)
        self.changed.emit()
        return pid

    def delete_protocol(self, protocol_id: str) -> bool:
        res = self._manager.delete_protocol(protocol_id)
        if res:
            self.changed.emit()
        return res

    def execute_protocol(self, protocol_data: dict[str, Any] | str) -> str:
        """Запускает протокол на выполнение (для кнопки 'Тест' в UI)."""
        ollama_url = getattr(self._config, "ollama_url", None) if self._config else None
        model = self._config.get("model") if (self._config and hasattr(self._config, "get")) else None
        return StarkProtocols.execute_protocol(protocol_data, ollama_url=ollama_url, model=model)
