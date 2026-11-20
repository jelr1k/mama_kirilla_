from __future__ import annotations

import threading


class PermissionManager:
    """Читает разрешения инструментов из ConfigManager.

    Проверка выполняется здесь и повторно в ToolExecutor, чтобы отключение
    инструмента через UI нельзя было обойти только изменением маршрута команды.
    """

    def __init__(self, config):
        self.config = config
        self._lock = threading.RLock()

    def is_enabled(self, tool_name: str) -> bool:
        with self._lock:
            tools = self.config.get("tools", {})
            return bool(tools.get(tool_name, False))

    def update(self, tool_name: str, enabled: bool) -> None:
        with self._lock:
            self.config.data.setdefault("tools", {})[tool_name] = bool(enabled)
            self.config.save()

    def update_many(self, tool_names, enabled: bool) -> None:
        with self._lock:
            tools_cfg = self.config.data.setdefault("tools", {})
            state = bool(enabled)
            for tool_name in tool_names:
                tools_cfg[tool_name] = state
            self.config.save()
