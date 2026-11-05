from __future__ import annotations

from typing import Any


def get_main_keyboard() -> dict[str, Any]:
    return {
        "keyboard": [
            [{"text": "📊 Статус ПК"}, {"text": "📸 Скриншот"}],
            [{"text": "📡 Сеть / Пинг"}, {"text": "🛡️ VPN / Запрет"}],
            [{"text": "🔒 Блокировка"}, {"text": "💤 Сон"}, {"text": "🔌 Выключение"}],
        ],
        "resize_keyboard": True,
        "is_persistent": True,
    }


def get_vpn_keyboard() -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "🚀 Запустить Запрет", "callback_data": "vpn:zapret"},
            ],
            [
                {"text": "⚡ Happ (Connect)", "callback_data": "vpn:happ"},
                {"text": "⚡ FlClashX (Connect)", "callback_data": "vpn:flclash"},
            ],
            [
                {"text": "🔄 Обновить статус", "callback_data": "vpn:status"},
            ],
        ]
    }


def get_shutdown_keyboard() -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "⏱️ Через 1 мин", "callback_data": "shutdown:1"},
                {"text": "⏱️ Через 5 мин", "callback_data": "shutdown:5"},
                {"text": "⏱️ Через 15 мин", "callback_data": "shutdown:15"},
            ],
            [
                {"text": "⚡ Выключить сейчас", "callback_data": "shutdown:0"},
                {"text": "🔄 Перезагрузка (1 мин)", "callback_data": "shutdown:reboot"},
            ],
            [
                {"text": "❌ Отменить выключение", "callback_data": "shutdown:cancel"},
            ],
        ]
    }


def get_cancel_shutdown_keyboard() -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "❌ Отменить выключение / перезагрузку", "callback_data": "shutdown:cancel"}
            ]
        ]
    }
