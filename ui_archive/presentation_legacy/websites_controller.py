from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from core.website_manager import WebsiteManager


class WebsitesController(QObject):
    changed = Signal()

    def __init__(self, manager: WebsiteManager):
        super().__init__()
        self._manager = manager

    def get_websites(self) -> list[dict]:
        return self._manager.get_websites()

    def add_website(self, name: str, url: str, aliases: list[str] | None = None, auto_aliases: bool = True) -> dict:
        result = self._manager.add_website(name, url, aliases, auto_aliases)
        self.changed.emit()
        return result

    def update_website(self, site_id: str, name: str, url: str, aliases: list[str]) -> bool:
        result = self._manager.update_website(site_id, name, url, aliases)
        if result:
            self.changed.emit()
        return result

    def delete_website(self, site_id: str) -> bool:
        result = self._manager.delete_website(site_id)
        if result:
            self.changed.emit()
        return result

    def reset_to_defaults(self) -> None:
        self._manager.reset_to_defaults()
        self.changed.emit()

    def generate_auto_aliases(self, url: str, name: str = "") -> list[str]:
        return self._manager.generate_auto_aliases(url, name)
