from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger("jarvis.voice.prompt_builder")


class VoicePromptBuilder:
    """Dynamically builds keyword prompt for Whisper speech recognition from active managers.

    Collects assistant names, application aliases, website names, and protocol phrases.
    Does not reload models and has zero impact on initialization time.
    """

    def __init__(
        self,
        alias_manager: Any = None,
        website_manager: Any = None,
        protocols_manager: Any = None,
        steam_manager: Any = None,
        app_indexer: Any = None,
        config: Any = None,
        cache_ttl: float = 15.0,
    ):
        self.alias_manager = alias_manager
        self.website_manager = website_manager
        self.protocols_manager = protocols_manager
        self.steam_manager = steam_manager
        self.app_indexer = app_indexer
        self.config = config
        self.cache_ttl = cache_ttl

        self._cached_prompt: str = ""
        self._last_built: float = 0.0

    def _ensure_managers(self) -> None:
        """Lazily load managers if not injected."""
        if self.alias_manager is None:
            try:
                from core.alias_manager import AliasManager
                self.alias_manager = AliasManager()
            except Exception:
                pass
        if self.website_manager is None:
            try:
                from core.website_manager import WebsiteManager
                self.website_manager = WebsiteManager()
            except Exception:
                pass
        if self.protocols_manager is None:
            try:
                from core.protocols_manager import ProtocolsManager
                self.protocols_manager = ProtocolsManager()
            except Exception:
                pass
        if self.app_indexer is None:
            try:
                from core.app_indexer import AppIndexer
                self.app_indexer = AppIndexer.get_instance()
            except Exception:
                pass
        if self.config is None:
            try:
                from core.config_manager import ConfigManager
                self.config = ConfigManager()
            except Exception:
                pass

    @staticmethod
    def _clean_word(word: str) -> str:
        if not word:
            return ""
        cleaned = word.replace(".lnk", "").replace(".exe", "").replace(".url", "").replace(".bat", "")
        cleaned = cleaned.strip(" .,!?:;\t\n\r\"'()[]{}")
        return cleaned

    def build_prompt(self, max_words: int = 70, max_chars: int = 500, force: bool = False) -> str:
        """Return a de-duplicated comma-separated string of live keywords."""
        now = time.time()
        if not force and self._cached_prompt and (now - self._last_built) < self.cache_ttl:
            return self._cached_prompt

        self._ensure_managers()

        words: list[str] = []
        seen_lower: set[str] = set()

        def add_word(w: str) -> None:
            cleaned = self._clean_word(w)
            if not cleaned or len(cleaned) < 2:
                return
            lower = cleaned.lower()
            if lower not in seen_lower:
                seen_lower.add(lower)
                words.append(cleaned)

        # 1. Assistant names & identity
        assistant_name = None
        if self.config is not None:
            try:
                assistant_name = self.config.get("assistant_name")
            except Exception:
                pass
        if assistant_name:
            add_word(assistant_name)
        add_word("Кириешка")
        add_word("Джарвис")

        # 2. Applications and custom aliases
        if self.alias_manager is not None:
            try:
                data = getattr(self.alias_manager, "data", {})
                for cat in ("applications", "actions", "files"):
                    entries = data.get(cat, {})
                    for key, entry in entries.items():
                        add_word(key)
                        if isinstance(entry, dict):
                            for alias in entry.get("aliases", []):
                                add_word(alias)
            except Exception as exc:
                logger.debug("prompt_builder_alias_error: %s", exc)

        # 3. Protocols and trigger phrases
        if self.protocols_manager is not None:
            try:
                protocols = self.protocols_manager.get_protocols()
                for proto in protocols:
                    add_word(proto.get("name", ""))
                    for phrase in proto.get("phrases", []):
                        add_word(phrase)
            except Exception as exc:
                logger.debug("prompt_builder_protocols_error: %s", exc)

        # 4. Websites & aliases
        if self.website_manager is not None:
            try:
                websites = self.website_manager.get_websites()
                for site in websites:
                    add_word(site.get("name", ""))
                    for alias in site.get("aliases", []):
                        add_word(alias)
            except Exception as exc:
                logger.debug("prompt_builder_website_error: %s", exc)

        # 5. Steam games (top installed)
        if self.steam_manager is not None:
            try:
                games = getattr(self.steam_manager, "installed_games", [])
                if not games and hasattr(self.steam_manager, "scan_installed_games"):
                    games = self.steam_manager.scan_installed_games()
                for game in (games or [])[:20]:
                    add_word(game.get("name", ""))
            except Exception as exc:
                logger.debug("prompt_builder_steam_error: %s", exc)

        # 6. Installed Windows Applications (top indexed)
        if self.app_indexer is not None:
            try:
                apps = self.app_indexer.scan_installed_apps()
                for app in (apps or [])[:25]:
                    add_word(app.get("name", ""))
                    for alias in app.get("aliases", []):
                        add_word(alias)
            except Exception as exc:
                logger.debug("prompt_builder_apps_error: %s", exc)

        selected: list[str] = []
        current_len = 0
        for w in words[:max_words]:
            part_len = len(w) + (2 if selected else 0)
            if current_len + part_len > max_chars:
                break
            selected.append(w)
            current_len += part_len

        result = ", ".join(selected)
        self._cached_prompt = result
        self._last_built = now
        return result
