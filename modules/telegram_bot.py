from __future__ import annotations

import logging
import threading

from modules.telegram.client import chunk_text
from modules.telegram.handlers import _router_route_lock
from modules.telegram.keyboards import (
    get_cancel_shutdown_keyboard,
    get_main_keyboard,
    get_shutdown_keyboard,
    get_vpn_keyboard,
)
from modules.telegram.service import TelegramBotService

logger = logging.getLogger("jarvis.telegram_bot")

# Backwards compatibility alias
TelegramBotModule = TelegramBotService

_global_telegram_bot: TelegramBotModule | None = None
_global_telegram_bot_lock = threading.Lock()


def get_telegram_bot(config_manager=None, app_context=None) -> TelegramBotModule:
    """Thread-safe singleton accessor for TelegramBotModule."""
    global _global_telegram_bot
    with _global_telegram_bot_lock:
        if _global_telegram_bot is None:
            _global_telegram_bot = TelegramBotModule(config_manager=config_manager, app_context=app_context)
        else:
            if config_manager and not _global_telegram_bot.config_manager:
                _global_telegram_bot.config_manager = config_manager
            if app_context and not _global_telegram_bot.app_context:
                _global_telegram_bot.app_context = app_context
        return _global_telegram_bot


__all__ = [
    "TelegramBotModule",
    "TelegramBotService",
    "get_telegram_bot",
    "_global_telegram_bot",
    "_global_telegram_bot_lock",
    "_router_route_lock",
    "chunk_text",
    "get_main_keyboard",
    "get_vpn_keyboard",
    "get_shutdown_keyboard",
    "get_cancel_shutdown_keyboard",
]
