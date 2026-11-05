from __future__ import annotations

from modules.telegram.client import TelegramClientMixin, chunk_text
from modules.telegram.handlers import TelegramCommandHandlerMixin
from modules.telegram.keyboards import (
    get_cancel_shutdown_keyboard,
    get_main_keyboard,
    get_shutdown_keyboard,
    get_vpn_keyboard,
)
from modules.telegram.service import TelegramBotService

TelegramBotModule = TelegramBotService

__all__ = [
    "TelegramBotService",
    "TelegramBotModule",
    "TelegramClientMixin",
    "TelegramCommandHandlerMixin",
    "chunk_text",
    "get_main_keyboard",
    "get_vpn_keyboard",
    "get_shutdown_keyboard",
    "get_cancel_shutdown_keyboard",
]
