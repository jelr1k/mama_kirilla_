from __future__ import annotations

from typing import Any


def get_main_keyboard() -> dict[str, Any]:
    return {
        "keyboard": [
            [{"text": "📊 Статус ПК"}, {"text": "📸 Скриншот"}],
            [{"text": "📡 Сеть / Пинг"}, {"text": "🛡️ VPN / Запрет"}],
            [{"text": "⚡ Протоколы"}, {"text": "🎵 Медиа"}, {"text": "📜 Команды"}],
            [{"text": "🔒 Блокировка"}, {"text": "💤 Сон"}, {"text": "🔌 Выключение"}],
        ],
        "resize_keyboard": True,
        "is_persistent": True,
    }


def get_media_keyboard() -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "⏮️ Пред", "callback_data": "media:prev_track"},
                {"text": "⏯️ Пауза / Плей", "callback_data": "media:play_pause"},
                {"text": "⏭️ След", "callback_data": "media:next_track"},
            ],
            [
                {"text": "🔉 Тише", "callback_data": "media:volume_down"},
                {"text": "🔇 Звук", "callback_data": "media:toggle_mute"},
                {"text": "🔊 Громче", "callback_data": "media:volume_up"},
            ],
        ]
    }


def get_protocols_keyboard(protocols: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[list[dict[str, str]]] = []
    current_row: list[dict[str, str]] = []
    for proto in protocols:
        pid = str(proto.get("id") or "").strip()
        name = str(proto.get("name") or pid).strip()
        if not pid:
            continue
        callback_data = f"protocol:{pid}"
        if len(callback_data.encode("utf-8")) > 64:
            continue
        current_row.append({"text": f"⚡ {name}", "callback_data": callback_data})
        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []
    if current_row:
        rows.append(current_row)
    return {"inline_keyboard": rows}


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
